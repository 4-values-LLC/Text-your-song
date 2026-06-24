"""Lädt die Quell-Audiodatei zum Suno-File-Host und liefert die öffentliche URL.

Nutzt den file-stream-upload-Endpunkt von sunoapi.org, der eine öffentliche
``downloadUrl`` zurückgibt (Datei ~3 Tage gültig). Damit ist keine eigene
S3-/Tunnel-Infrastruktur nötig.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from txtsong.config import get_settings
from txtsong.utils.logging import get_logger

log = get_logger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=16))
def upload_audio(audio_path: Path, *, api_key: str | None = None) -> str:
    """Lädt ``audio_path`` hoch und gibt die öffentliche Download-URL zurück."""
    settings = get_settings()
    key = api_key or settings.suno_api_key
    if not key:
        raise RuntimeError("SUNO_API_KEY ist nicht gesetzt.")

    log.info("Lade Audio zu Suno-File-Host: %s", audio_path.name)
    with open(audio_path, "rb") as fh:
        files = {"file": (audio_path.name, fh, "audio/wav")}
        data = {"uploadPath": "user-uploads", "fileName": audio_path.name}
        resp = httpx.post(
            settings.suno_upload_url,
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data,
            timeout=120,
        )
    resp.raise_for_status()
    payload = resp.json()
    download_url = (payload.get("data") or {}).get("downloadUrl")
    if not download_url:
        raise RuntimeError(f"Upload lieferte keine downloadUrl: {payload}")
    log.info("Upload erfolgreich -> %s", download_url)
    return download_url
