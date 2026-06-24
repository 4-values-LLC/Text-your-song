"""Ingest aus lokaler Datei (Upload)."""

from __future__ import annotations

from pathlib import Path

from txtsong.ingest.base import IngestResult
from txtsong.models.blueprint import Source
from txtsong.utils import audio
from txtsong.utils.workspace import Workspace


def ingest_local(path: Path, ws: Workspace) -> IngestResult:
    """Validiert eine lokale Audiodatei und transcodiert sie nach source.wav."""
    if not path.exists():
        raise FileNotFoundError(f"Audiodatei nicht gefunden: {path}")

    audio.to_wav(path, ws.source_audio)
    duration = audio.probe_duration(ws.source_audio)
    source = Source(
        origin="local",
        title=path.stem,
        duration_s=duration,
        sample_rate=audio.CANONICAL_SR,
    )
    return IngestResult(source_wav=ws.source_audio, source=source)
