"""Audio-Hilfsfunktionen (Transcodierung & Trimmen via ffmpeg)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from txtsong.utils.logging import get_logger

log = get_logger(__name__)

CANONICAL_SR = 44100


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def to_wav(src: Path, dst: Path, *, sample_rate: int = CANONICAL_SR) -> Path:
    """Transcodiert eine beliebige Audiodatei in eine kanonische WAV-Datei.

    Erfordert ffmpeg im PATH.
    """
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg wurde nicht gefunden. Bitte ffmpeg installieren "
            "(z. B. 'apt-get install ffmpeg')."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ar", str(sample_rate), "-ac", "2",
        str(dst),
    ]
    log.info("ffmpeg transcodiert %s -> %s", src.name, dst.name)
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def trim(src: Path, dst: Path, *, max_seconds: float) -> Path:
    """Schneidet die Datei auf max. ``max_seconds`` (für Suno-Längenlimits)."""
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg wurde nicht gefunden.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-t", str(max_seconds),
        "-ar", str(CANONICAL_SR), "-ac", "2",
        str(dst),
    ]
    log.info("ffmpeg trimmt %s auf %.0fs", src.name, max_seconds)
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def probe_duration(src: Path) -> float | None:
    """Liest die Dauer einer Datei via ffprobe (oder None bei Fehler)."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(src),
            ],
            check=True, capture_output=True, text=True,
        )
        return float(out.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None
