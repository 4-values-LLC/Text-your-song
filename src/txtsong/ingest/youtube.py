"""Ingest aus YouTube via yt-dlp."""

from __future__ import annotations

from pathlib import Path

from txtsong.ingest.base import IngestResult
from txtsong.models.blueprint import Source
from txtsong.utils import audio
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import Workspace

log = get_logger(__name__)


def download_youtube(url: str, ws: Workspace) -> IngestResult:
    """Lädt das beste Audio einer YouTube-URL und transcodiert nach source.wav."""
    import yt_dlp  # lazy import

    out_template = str(ws.root / "yt_source.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    log.info("Lade YouTube-Audio: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded = Path(ydl.prepare_filename(info))

    # In kanonisches WAV umwandeln.
    audio.to_wav(downloaded, ws.source_audio)
    downloaded.unlink(missing_ok=True)

    source = Source(
        origin="youtube",
        url=url,
        title=info.get("title"),
        artist=info.get("uploader") or info.get("channel"),
        duration_s=float(info["duration"]) if info.get("duration") else None,
        sample_rate=audio.CANONICAL_SR,
    )
    return IngestResult(source_wav=ws.source_audio, source=source)
