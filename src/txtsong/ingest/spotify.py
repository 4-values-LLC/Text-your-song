"""Ingest aus Spotify.

Spotify-Audio kann nicht direkt heruntergeladen werden. Daher wird der Track
über Metadaten (Titel + Artist) identifiziert und per yt-dlp-Suche auf YouTube
gematcht (Dauer-Abgleich, "best effort").
"""

from __future__ import annotations

import httpx

from txtsong.config import get_settings
from txtsong.ingest.base import IngestResult
from txtsong.ingest.youtube import download_youtube
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import Workspace

log = get_logger(__name__)


def _metadata_via_oembed(url: str) -> tuple[str | None, str | None]:
    """Holt Titel (und ggf. Artist) ohne Auth über Spotify oEmbed."""
    try:
        resp = httpx.get(
            "https://open.spotify.com/oembed", params={"url": url}, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        # oEmbed liefert "title" meist als "Songtitel" (ohne Artist).
        return data.get("title"), data.get("author_name")
    except httpx.HTTPError as exc:
        log.warning("Spotify oEmbed fehlgeschlagen: %s", exc)
        return None, None


def _metadata_via_api(url: str) -> tuple[str | None, str | None]:
    """Holt Titel + Artist über die Spotify-Web-API (falls Credentials gesetzt)."""
    settings = get_settings()
    if not (settings.spotify_client_id and settings.spotify_client_secret):
        return None, None
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=settings.spotify_client_id,
                client_secret=settings.spotify_client_secret,
            )
        )
        track = sp.track(url)
        artist = ", ".join(a["name"] for a in track["artists"])
        return track["name"], artist
    except Exception as exc:  # spotipy wirft diverse Fehler
        log.warning("Spotify-API fehlgeschlagen: %s", exc)
        return None, None


def resolve_spotify(url: str, ws: Workspace) -> IngestResult:
    """Spotify-URL -> Metadaten -> YouTube-Match -> Download."""
    title, artist = _metadata_via_api(url)
    if not title:
        title, artist = _metadata_via_oembed(url)
    if not title:
        raise RuntimeError(
            "Spotify-Track konnte nicht aufgelöst werden. Bitte stattdessen einen "
            "YouTube-Link oder eine Audiodatei verwenden."
        )

    query = f"{artist} {title}".strip() if artist else title
    log.info("Spotify -> YouTube-Suche: %s", query)
    # yt-dlp kann direkt über "ytsearch1:" suchen und das beste Ergebnis laden.
    result = download_youtube(f"ytsearch1:{query}", ws)
    # Quelle als spotify markieren, Original-Metadaten beibehalten.
    result.source.origin = "spotify"
    result.source.url = url
    result.source.title = title
    result.source.artist = artist
    return result
