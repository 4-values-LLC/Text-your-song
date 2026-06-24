"""Pollt einen Suno-Task bis zur Fertigstellung und lädt die Tracks herunter."""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from txtsong.models.suno import CoverResult
from txtsong.suno.client import SunoClient
from txtsong.utils.logging import get_logger

log = get_logger(__name__)


def download_track(audio_url: str, dst: Path) -> Path:
    """Lädt eine Audiodatei herunter."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", audio_url, timeout=120, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dst, "wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)
    return dst


def poll_until_complete(
    client: SunoClient,
    task_id: str,
    *,
    interval_s: float = 15.0,
    timeout_s: float = 600.0,
    on_update=None,
) -> CoverResult:
    """Pollt ``record-info`` bis Status ``complete`` oder ``error``.

    ``on_update(result)`` wird bei jeder Status-Änderung aufgerufen (optional).
    """
    deadline = time.monotonic() + timeout_s
    last_status = None
    while time.monotonic() < deadline:
        result = client.get_result(task_id)
        if result.status != last_status:
            log.info("Suno-Task %s: Status=%s", task_id, result.status)
            last_status = result.status
            if on_update:
                on_update(result)
        if result.status == "complete":
            return result
        if result.status == "error":
            raise RuntimeError(f"Suno-Task fehlgeschlagen: {result.error}")
        time.sleep(interval_s)
    raise TimeoutError(f"Suno-Task {task_id} nicht innerhalb {timeout_s}s fertig.")


def fetch_results(client: SunoClient, result: CoverResult, result_dir: Path) -> CoverResult:
    """Lädt alle Tracks eines fertigen Ergebnisses in result_dir."""
    result_dir.mkdir(parents=True, exist_ok=True)
    for i, track in enumerate(result.tracks):
        if not track.audio_url:
            continue
        dst = result_dir / f"remix_{i + 1}.mp3"
        log.info("Lade Remix-Track %d herunter ...", i + 1)
        download_track(track.audio_url, dst)
        track.local_path = str(dst)
    return result
