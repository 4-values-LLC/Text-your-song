"""Zentrale Konfiguration (aus Umgebung / .env geladen)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Erlaubte Suno-Modelle und ihre Limits (siehe Suno-API-Doku).
# audio_max_s = maximale Länge der hochgeladenen Quell-Audiodatei.
SUNO_MODEL_LIMITS: dict[str, dict[str, int]] = {
    "V4": {"prompt": 3000, "style": 200, "title": 80, "audio_max_s": 480},
    "V4_5": {"prompt": 5000, "style": 1000, "title": 100, "audio_max_s": 480},
    "V4_5PLUS": {"prompt": 5000, "style": 1000, "title": 100, "audio_max_s": 480},
    "V4_5ALL": {"prompt": 5000, "style": 1000, "title": 80, "audio_max_s": 60},
    "V5": {"prompt": 5000, "style": 1000, "title": 100, "audio_max_s": 480},
    "V5_5": {"prompt": 5000, "style": 1000, "title": 100, "audio_max_s": 480},
}


class Settings(BaseSettings):
    """Anwendungs-Einstellungen."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Suno ---
    suno_api_key: str = ""
    suno_base_url: str = "https://api.sunoapi.org"
    suno_upload_url: str = "https://sunoapiorg.redpandaai.co/api/file-stream-upload"
    suno_model: str = "V5"
    suno_audio_weight: float = 0.65
    suno_style_weight: float = 0.6
    suno_weirdness: float = 0.3
    suno_callback_url: str = ""

    # --- Analyse ---
    demucs_enabled: bool = True
    whisper_enabled: bool = True
    whisper_model: str = "base"
    demucs_model: str = "htdemucs"

    # --- Infrastruktur ---
    workspace_dir: Path = Field(default=Path("./workspace"))
    redis_url: str = "redis://localhost:6379/0"
    use_queue: bool = False

    # --- Spotify (optional) ---
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    @property
    def model_limits(self) -> dict[str, int]:
        """Limits für das aktuell konfigurierte Suno-Modell."""
        return SUNO_MODEL_LIMITS.get(self.suno_model, SUNO_MODEL_LIMITS["V4_5PLUS"])


@lru_cache
def get_settings() -> Settings:
    """Gecachte Settings-Instanz."""
    return Settings()
