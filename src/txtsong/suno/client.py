"""Suno-API-Client: upload-cover absenden + Ergebnis pollen.

Endpunkte (sunoapi.org):
- POST {base}/api/v1/generate/upload-cover        -> {data.taskId}
- GET  {base}/api/v1/generate/record-info?taskId  -> Status + sunoData[]
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from txtsong.config import SUNO_MODEL_LIMITS, get_settings
from txtsong.models.suno import CoverResult, SunoRequest, SunoTrack
from txtsong.utils.logging import get_logger

log = get_logger(__name__)

# record-info status -> normalisierter Status für CoverResult.
_STATUS_MAP = {
    "PENDING": "pending",
    "TEXT_SUCCESS": "text",
    "FIRST_SUCCESS": "first",
    "SUCCESS": "complete",
    "CREATE_TASK_FAILED": "error",
    "GENERATE_AUDIO_FAILED": "error",
    "CALLBACK_EXCEPTION": "error",
    "SENSITIVE_WORD_ERROR": "error",
}


class SunoValidationError(ValueError):
    """Pre-Flight-Validierung des Requests fehlgeschlagen."""


def validate_request(req: SunoRequest) -> None:
    """Prüft alle Längen-/Enum-/Pflichtfeld-Constraints VOR dem API-Call."""
    if req.model not in SUNO_MODEL_LIMITS:
        raise SunoValidationError(f"Unbekanntes Modell: {req.model}")
    limits = SUNO_MODEL_LIMITS[req.model]
    if not req.upload_url:
        raise SunoValidationError("upload_url fehlt.")
    if req.custom_mode:
        if not req.style:
            raise SunoValidationError("style ist im Custom-Mode Pflicht.")
        if not req.title:
            raise SunoValidationError("title ist im Custom-Mode Pflicht.")
        if not req.instrumental and not req.prompt:
            raise SunoValidationError("prompt (Lyrics) fehlt (nicht instrumental).")
    if len(req.style) > limits["style"]:
        raise SunoValidationError(
            f"style zu lang: {len(req.style)} > {limits['style']}"
        )
    if len(req.title) > limits["title"]:
        raise SunoValidationError(
            f"title zu lang: {len(req.title)} > {limits['title']}"
        )
    if req.prompt and len(req.prompt) > limits["prompt"]:
        raise SunoValidationError(
            f"prompt zu lang: {len(req.prompt)} > {limits['prompt']}"
        )


class SunoClient:
    """Dünner HTTP-Client um die sunoapi.org-Endpunkte."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.suno_api_key
        self.base_url = (base_url or settings.suno_base_url).rstrip("/")
        if not self.api_key:
            raise RuntimeError("SUNO_API_KEY ist nicht gesetzt.")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=16))
    def submit_cover(self, req: SunoRequest) -> str:
        """Sendet den upload-cover-Request und gibt die taskId zurück."""
        validate_request(req)
        url = f"{self.base_url}/api/v1/generate/upload-cover"
        log.info("Sende upload-cover an Suno (Modell %s) ...", req.model)
        resp = httpx.post(url, headers=self._headers, json=req.to_api_payload(), timeout=60)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 200:
            raise RuntimeError(f"Suno-Fehler: {body.get('msg')} ({body})")
        task_id = (body.get("data") or {}).get("taskId")
        if not task_id:
            raise RuntimeError(f"Keine taskId in Antwort: {body}")
        return task_id

    def get_result(self, task_id: str) -> CoverResult:
        """Fragt den aktuellen Status/Ergebnis eines Tasks ab."""
        url = f"{self.base_url}/api/v1/generate/record-info"
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"taskId": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") or {}
        raw_status = data.get("status", "PENDING")
        status = _STATUS_MAP.get(raw_status, "pending")

        tracks: list[SunoTrack] = []
        for item in (data.get("response") or {}).get("sunoData", []) or []:
            tracks.append(
                SunoTrack(
                    id=item.get("id"),
                    audio_url=item.get("audioUrl") or item.get("streamAudioUrl"),
                    image_url=item.get("imageUrl"),
                    title=item.get("title"),
                    duration=item.get("duration"),
                )
            )

        return CoverResult(
            task_id=task_id,
            status=status,
            tracks=tracks,
            error=data.get("errorMessage"),
        )
