"""Assembliert die Teil-Analysen zu einem vollständigen SongBlueprint."""

from __future__ import annotations

from datetime import datetime, timezone

import librosa

from txtsong.analysis.features import AudioFeatures, extract_features
from txtsong.analysis.structure import detect_structure
from txtsong.config import get_settings
from txtsong.models.blueprint import (
    AnalysisMeta,
    Dynamics,
    Production,
    SongBlueprint,
    Source,
    Spectral,
    Tempo,
    Tonality,
    Vocals,
)
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import Workspace

log = get_logger(__name__)


def _infer_mood(feat: AudioFeatures) -> list[str]:
    """Grobe Stimmungs-Heuristik aus Tempo, Tonart, Helligkeit, Energie."""
    mood: list[str] = []
    if feat.bpm >= 125:
        mood.append("energetic")
    elif feat.bpm <= 85:
        mood.append("laid-back")
    mood.append("uplifting" if feat.scale == "major" else "melancholic")
    if feat.brightness == "bright":
        mood.append("bright")
    elif feat.brightness == "dark":
        mood.append("moody")
    return mood[:3]


def _infer_genre(feat: AudioFeatures) -> tuple[str, str]:
    """Sehr grobe Genre-Heuristik aus Tempo & Spektrum (Platzhalter ohne ML-Klassifikator)."""
    bpm = feat.bpm
    if bpm >= 124 and feat.brightness != "dark":
        return "electronic / dance", "edm"
    if 90 <= bpm <= 110 and feat.dynamic_range == "compressed":
        return "pop", "modern pop"
    if bpm <= 90 and feat.brightness == "dark":
        return "ballad / r&b", "soul"
    if bpm >= 140:
        return "rock / drum & bass", "uptempo"
    return "pop", "contemporary"


def build_blueprint_from_features(
    feat: AudioFeatures, source: Source, *, demucs_used: bool, whisper_used: bool
) -> SongBlueprint:
    """Baut den Blueprint aus den librosa-Features + Quelle (ohne Stems/Whisper)."""
    structure = detect_structure(feat.y, feat.sr, feat.duration_s, bpm=feat.bpm)
    genre, subgenre = _infer_genre(feat)

    source.duration_s = source.duration_s or feat.duration_s
    source.sample_rate = source.sample_rate or feat.sr

    return SongBlueprint(
        source=source,
        tempo=Tempo(
            bpm=feat.bpm,
            bpm_confidence=feat.bpm_confidence,
            time_signature="4/4",  # heuristische Annahme
            tempo_stability=feat.tempo_stability,
            beat_times_s=feat.beat_times,
        ),
        tonality=Tonality(
            key=feat.key,
            scale=feat.scale,
            key_confidence=feat.key_confidence,
        ),
        structure=structure,
        dynamics=Dynamics(
            energy_curve=feat.energy_curve,
            loudness_lufs_est=feat.loudness_lufs_est,
            rms_peak=feat.rms_peak,
            dynamic_range=feat.dynamic_range,
        ),
        spectral=Spectral(
            centroid_hz_mean=feat.centroid_hz,
            brightness=feat.brightness,
            rolloff_hz=feat.rolloff_hz,
        ),
        production=Production(
            genre=genre,
            subgenre=subgenre,
            mood=_infer_mood(feat),
            era="2010s",  # heuristische Annahme; kann via Klassifikator verbessert werden
        ),
        vocals=Vocals(present=None),
        analysis_meta=AnalysisMeta(
            demucs_used=demucs_used,
            whisper_used=whisper_used,
            generated_at=datetime.now(timezone.utc).isoformat(),
            librosa_version=librosa.__version__,
        ),
    )


def analyze_song(ws: Workspace, source: Source) -> SongBlueprint:
    """Volle Analyse-Pipeline: librosa-Features + optional Demucs + optional Whisper.

    Speichert ``blueprint.json`` im Workspace und gibt den Blueprint zurück.
    """
    settings = get_settings()
    audio_path = str(ws.source_audio)

    log.info("Analysiere Audio-Features (librosa) ...")
    ws.write_status("analyse", 40, "Analysiere Tempo, Tonart, Struktur ...")
    feat = extract_features(audio_path)

    blueprint = build_blueprint_from_features(
        feat, source, demucs_used=False, whisper_used=False
    )

    # --- Optional: Stem-Trennung (Demucs) ---
    if settings.demucs_enabled:
        try:
            from txtsong.analysis.stems import analyze_stems

            ws.write_status("stems", 60, "Trenne Stems (Demucs) ...")
            analyze_stems(ws, blueprint)
            blueprint.analysis_meta.demucs_used = True
        except Exception as exc:  # Demucs ist optional / schwer
            log.warning("Demucs übersprungen: %s", exc)

    # --- Optional: Transkription (Whisper) ---
    if settings.whisper_enabled:
        try:
            from txtsong.analysis.transcribe import transcribe_vocals

            ws.write_status("transcribe", 75, "Transkribiere Originaltext (Whisper) ...")
            transcribe_vocals(ws, blueprint)
            blueprint.analysis_meta.whisper_used = True
        except Exception as exc:
            log.warning("Whisper übersprungen: %s", exc)

    ws.blueprint_path.write_text(blueprint.to_json(), encoding="utf-8")
    log.info("Blueprint gespeichert: %s", ws.blueprint_path)
    return blueprint
