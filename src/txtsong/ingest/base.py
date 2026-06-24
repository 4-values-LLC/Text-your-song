"""Gemeinsame Typen & Dispatcher für die Ingest-Stufe."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from txtsong.models.blueprint import Source
from txtsong.utils.workspace import Workspace


@dataclass
class IngestResult:
    """Ergebnis der Ingest-Stufe."""

    source_wav: Path
    source: Source


_SPOTIFY_RE = re.compile(r"open\.spotify\.com|spotify:", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def classify_input(value: str) -> str:
    """Bestimmt den Typ einer Eingabe: 'spotify' | 'url' | 'local'.

    Spotify ist ein Sonderfall (Metadaten -> YouTube-Match). Jede andere
    http(s)-URL wird über yt-dlp aufgelöst, das hunderte Dienste unterstützt
    (YouTube, SoundCloud, Bandcamp, Vimeo, Dailymotion u. v. m.). Alles andere
    gilt als lokaler Dateipfad.
    """
    if _SPOTIFY_RE.search(value):
        return "spotify"
    if _URL_RE.search(value.strip()):
        return "url"
    return "local"


def resolve_source(value: str, ws: Workspace) -> IngestResult:
    """Beschafft das Quell-Audio passend zum Eingabetyp und legt ``source.wav`` an.

    Imports der konkreten Backends erfolgen lazy, damit z. B. yt-dlp nicht für
    reine Datei-Uploads benötigt wird.
    """
    kind = classify_input(value)
    if kind == "spotify":
        from txtsong.ingest.spotify import resolve_spotify

        return resolve_spotify(value, ws)
    if kind == "url":
        from txtsong.ingest.youtube import download_url

        return download_url(value, ws)
    from txtsong.ingest.local import ingest_local

    return ingest_local(Path(value), ws)
