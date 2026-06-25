"""Orchestrator: verbindet alle Stufen (Ingest -> Analyse -> Prompt -> Suno).

Bietet zwei Haupt-Operationen:
- ``run_analysis``  : Ingest + volle Analyse -> Blueprint + Report + Lyric-Template
- ``run_remix``     : Style/Lyrics bauen -> Audio hochladen -> upload-cover -> Ergebnis
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from txtsong.analysis import analyze_song
from txtsong.config import get_settings
from txtsong.ingest import resolve_source
from txtsong.models.blueprint import SongBlueprint
from txtsong.models.suno import CoverResult, SunoRequest
from txtsong.prompt.lyric_aligner import align_lyrics, clamp_prompt
from txtsong.prompt.lyrics_template import build_template, template_as_text
from txtsong.prompt.style_builder import (
    build_style,
    derive_negative_tags,
    derive_title,
    derive_vocal_gender,
)
from txtsong.report import render_report
from txtsong.suno.client import SunoClient
from txtsong.suno.poller import fetch_results, poll_until_complete
from txtsong.suno.upload import upload_audio
from txtsong.utils import audio as audio_utils
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import Workspace, get_workspace

log = get_logger(__name__)


@dataclass
class AnalysisResult:
    job_id: str
    blueprint: SongBlueprint
    report_md: str
    template_text: str


def run_analysis(source_input: str, job_id: str | None = None) -> AnalysisResult:
    """Stufe A–D (ohne Suno): Song beschaffen, analysieren, Report + Template erzeugen."""
    ws = get_workspace(job_id)
    ws.write_status("ingest", 10, "Beschaffe Quell-Audio ...")
    ingest = resolve_source(source_input, ws)

    blueprint = analyze_song(ws, ingest.source)

    ws.write_status("report", 90, "Erstelle Producer-Report ...")
    report_md = render_report(blueprint)
    ws.report_path.write_text(report_md, encoding="utf-8")

    template = build_template(blueprint)
    template_text = template_as_text(template)

    ws.write_status("done_analysis", 100, "Analyse abgeschlossen.")
    return AnalysisResult(
        job_id=ws.job_id,
        blueprint=blueprint,
        report_md=report_md,
        template_text=template_text,
    )


def build_request(
    ws: Workspace,
    blueprint: SongBlueprint,
    user_lyrics: str,
    *,
    upload_url: str,
    instrumental: bool = False,
) -> SunoRequest:
    """Baut (und speichert) den vollständigen SunoRequest aus Blueprint + Text.

    ``instrumental`` bezieht sich auf die gewünschte Ausgabe: bei ``True`` wird
    ein vocal-loser Remix erzeugt und der Nutzertext ignoriert.
    """
    settings = get_settings()
    limits = settings.model_limits

    template = build_template(blueprint)
    aligned = align_lyrics(template, user_lyrics)
    prompt = "" if instrumental else clamp_prompt(aligned.to_suno_prompt(), max_len=limits["prompt"])

    req = SunoRequest(
        upload_url=upload_url,
        style=build_style(blueprint, max_len=limits["style"], instrumental=instrumental),
        title=derive_title(blueprint, max_len=limits["title"]),
        prompt=prompt,
        model=settings.suno_model,
        custom_mode=True,
        instrumental=instrumental,
        callback_url=settings.suno_callback_url or None,
        audio_weight=settings.suno_audio_weight,
        style_weight=settings.suno_style_weight,
        weirdness_constraint=settings.suno_weirdness,
        vocal_gender=derive_vocal_gender(blueprint),
        negative_tags=derive_negative_tags(blueprint),
    )
    ws.suno_request_path.write_text(req.model_dump_json(indent=2), encoding="utf-8")
    return req


def run_remix(
    job_id: str, user_lyrics: str, *, instrumental: bool = False, dry_run: bool = False
) -> CoverResult | SunoRequest:
    """Stufe D–E: Request bauen, Audio hochladen, upload-cover, Ergebnis holen.

    Mit ``instrumental=True`` wird ein vocal-loser Remix erzeugt (Nutzertext
    ignoriert). Mit ``dry_run=True`` wird nur der Request gebaut und
    zurückgegeben (kein API-Call).
    """
    ws = get_workspace(job_id, create=False)
    if not ws.blueprint_path.exists():
        raise FileNotFoundError(f"Kein Blueprint für Job {job_id}. Erst analysieren.")
    blueprint = SongBlueprint.from_json(ws.blueprint_path.read_text(encoding="utf-8"))
    ws.lyrics_path.write_text(user_lyrics, encoding="utf-8")

    settings = get_settings()

    # Quelle ggf. auf Suno-Längenlimit trimmen.
    upload_path = ws.source_audio
    duration = blueprint.source.duration_s or audio_utils.probe_duration(ws.source_audio)
    max_s = settings.model_limits["audio_max_s"]
    if duration and duration > max_s:
        trimmed = ws.root / "source_trimmed.wav"
        audio_utils.trim(ws.source_audio, trimmed, max_seconds=max_s)
        upload_path = trimmed

    if dry_run:
        # Platzhalter-URL, damit der Request validierbar ist.
        return build_request(
            ws, blueprint, user_lyrics,
            upload_url="https://dry-run.local/audio.wav", instrumental=instrumental,
        )

    ws.write_status("upload", 20, "Lade Audio zu Suno hoch ...")
    upload_url = upload_audio(upload_path)

    req = build_request(ws, blueprint, user_lyrics, upload_url=upload_url, instrumental=instrumental)

    ws.write_status("submit", 35, "Sende Remix-Auftrag an Suno ...")
    client = SunoClient()
    task_id = client.submit_cover(req)
    ws.write_status("generating", 50, "Suno produziert den Remix ...", task_id=task_id)

    def _progress(result: CoverResult) -> None:
        pct = {"pending": 50, "text": 60, "first": 80, "complete": 95}.get(result.status, 50)
        ws.write_status("generating", pct, f"Suno-Status: {result.status}", task_id=task_id)

    result = poll_until_complete(client, task_id, on_update=_progress)
    fetch_results(client, result, ws.result_dir)

    # Ergebnis-Metadaten speichern.
    ws.write_status(
        "done", 100, "Remix fertig.",
        task_id=task_id,
        tracks=[t.local_path for t in result.tracks if t.local_path],
    )
    (ws.result_dir / "result.json").write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
