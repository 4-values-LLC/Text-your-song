"""Transkription des isolierten Vocal-Stems via faster-whisper.

Liefert den Originaltext, die erkannte Sprache und – über die Segment-Zeitstempel –
die Zeilenzahl je Songsektion (für ein passgenaues Lyric-Template).
"""

from __future__ import annotations

from pathlib import Path

from txtsong.config import get_settings
from txtsong.models.blueprint import SongBlueprint
from txtsong.utils.logging import get_logger

log = get_logger(__name__)


def _vocal_source(ws) -> Path:
    """Bevorzugt den getrennten Vocal-Stem, sonst die Originaldatei."""
    settings = get_settings()
    stem = ws.stems_dir / settings.demucs_model / ws.source_audio.stem / "vocals.wav"
    return stem if stem.exists() else ws.source_audio


def transcribe_vocals(ws, blueprint: SongBlueprint) -> None:
    """Transkribiert die Vocals und reichert Blueprint + Sektionen an."""
    from faster_whisper import WhisperModel

    settings = get_settings()
    source = _vocal_source(ws)

    log.info("Lade Whisper-Modell '%s' ...", settings.whisper_model)
    model = WhisperModel(settings.whisper_model, device="auto", compute_type="int8")

    segments, info = model.transcribe(str(source), vad_filter=True)
    seg_list = list(segments)

    text = "\n".join(s.text.strip() for s in seg_list if s.text.strip())
    blueprint.vocals.lyrics_transcribed = text or None
    blueprint.vocals.language = getattr(info, "language", None)
    if blueprint.vocals.present is None:
        blueprint.vocals.present = bool(text)

    # Zeilen je Sektion über die Segment-Mittelpunkte zuordnen.
    sections = blueprint.structure.sections
    if sections and seg_list:
        counts = {sec.index: 0 for sec in sections}
        for seg in seg_list:
            mid = (seg.start + seg.end) / 2
            for sec in sections:
                if sec.start_s <= mid < sec.end_s:
                    counts[sec.index] += 1
                    break
        for sec in sections:
            sec.lyric_lines = counts.get(sec.index, 0)
