"""Ingest beliebiger unterstützter URLs via yt-dlp.

yt-dlp unterstützt hunderte Dienste (YouTube, SoundCloud, Bandcamp, Vimeo,
Dailymotion u. v. m.) sowie die Suche (``ytsearch1:...``). Dieses Modul lädt
das beste verfügbare Audio und transcodiert es in die kanonische ``source.wav``.
"""

from __future__ import annotations

from pathlib import Path

from txtsong.ingest.base import IngestResult
from txtsong.models.blueprint import Source
from txtsong.utils import audio
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import Workspace

log = get_logger(__name__)


def download_url(url: str, ws: Workspace) -> IngestResult:
    """Lädt das beste Audio einer beliebigen yt-dlp-URL und schreibt source.wav."""
    import yt_dlp  # lazy import

    out_template = str(ws.root / "dl_source.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    log.info("Lade Audio (yt-dlp): %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Bei Suche/Playlist liefert yt-dlp ein "entries"-Feld.
        if "entries" in info and info["entries"]:
            info = info["entries"][0]
        downloaded = Path(ydl.prepare_filename(info))

    audio.to_wav(downloaded, ws.source_audio)
    downloaded.unlink(missing_ok=True)

    # Dienst-Name (z. B. "youtube", "soundcloud") als origin verwenden.
    extractor = (info.get("extractor_key") or info.get("extractor") or "url").lower()
    origin = "youtube" if "youtube" in extractor else "url"

    source = Source(
        origin=origin,  # type: ignore[arg-type]
        url=info.get("webpage_url") or url,
        title=info.get("title"),
        artist=info.get("artist") or info.get("uploader") or info.get("channel"),
        duration_s=float(info["duration"]) if info.get("duration") else None,
        sample_rate=audio.CANONICAL_SR,
    )
    return IngestResult(source_wav=ws.source_audio, source=source)


# Rückwärtskompatibler Alias (Spotify-Backend nutzt yt-dlp-Suche).
def download_youtube(url: str, ws: Workspace) -> IngestResult:
    return download_url(url, ws)
