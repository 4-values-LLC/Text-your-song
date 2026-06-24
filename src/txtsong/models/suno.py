"""Modelle für die Suno-API (Request, Tracks, Ergebnis)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SunoRequest(BaseModel):
    """Vollständig vorbereiteter upload-cover-Request.

    Wird als ``suno_request.json`` gespeichert und kann vor dem Absenden noch
    editiert werden.
    """

    upload_url: str
    style: str
    title: str
    prompt: str  # = Lyrics
    model: str = "V4_5PLUS"
    custom_mode: bool = True
    instrumental: bool = False
    callback_url: str | None = None
    audio_weight: float | None = None
    style_weight: float | None = None
    weirdness_constraint: float | None = None
    vocal_gender: str | None = None  # "m" | "f"
    negative_tags: str | None = None

    def to_api_payload(self) -> dict:
        """In das von der Suno-API erwartete camelCase-JSON umwandeln."""
        payload: dict = {
            "uploadUrl": self.upload_url,
            "customMode": self.custom_mode,
            "instrumental": self.instrumental,
            "model": self.model,
            "style": self.style,
            "title": self.title,
            # callBackUrl ist laut Doku Pflicht; leerer Platzhalter ist erlaubt,
            # da das Ergebnis per Polling geholt wird.
            "callBackUrl": self.callback_url or "https://example.com/no-callback",
        }
        if not self.instrumental:
            payload["prompt"] = self.prompt
        if self.audio_weight is not None:
            payload["audioWeight"] = self.audio_weight
        if self.style_weight is not None:
            payload["styleWeight"] = self.style_weight
        if self.weirdness_constraint is not None:
            payload["weirdnessConstraint"] = self.weirdness_constraint
        if self.vocal_gender:
            payload["vocalGender"] = self.vocal_gender
        if self.negative_tags:
            payload["negativeTags"] = self.negative_tags
        return payload


class SunoTrack(BaseModel):
    """Ein einzelner von Suno generierter Track."""

    id: str | None = None
    audio_url: str | None = None
    image_url: str | None = None
    title: str | None = None
    duration: float | None = None
    local_path: str | None = None  # nach Download gesetzt


class CoverResult(BaseModel):
    """Ergebnis eines Cover-/Remix-Jobs."""

    task_id: str
    status: str = "pending"  # pending | text | first | complete | error
    tracks: list[SunoTrack] = Field(default_factory=list)
    error: str | None = None
