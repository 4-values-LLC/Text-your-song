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


_YOUTUBE_RE = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)
_SPOTIFY_RE = re.compile(r"open\.spotify\.com|spotify:", re.IGNORECASE)


def classify_input(value: str) -> str:
    """Bestimmt den Typ einer Eingabe: 'youtube' | 'spotify' | 'local'."""
    if _YOUTUBE_RE.search(value):
        return "youtube"
    if _SPOTIFY_RE.search(value):
        return "spotify"
    return "local"


def resolve_source(value: str, ws: Workspace) -> IngestResult:
    """Beschafft das Quell-Audio passend zum Eingabetyp und legt ``source.wav`` an.

    Imports der konkreten Backends erfolgen lazy, damit z. B. yt-dlp nicht für
    reine Datei-Uploads benötigt wird.
    """
    kind = classify_input(value)
    if kind == "youtube":
        from txtsong.ingest.youtube import download_youtube

        return download_youtube(value, ws)
    if kind == "spotify":
        from txtsong.ingest.spotify import resolve_spotify

        return resolve_spotify(value, ws)
    from txtsong.ingest.local import ingest_local

    return ingest_local(Path(value), ws)
