"""Pro-Job-Workspace: ein Verzeichnis je Analyse/Remix mit allen Artefakten."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from txtsong.config import get_settings


def new_job_id() -> str:
    """Erzeugt eine kurze, eindeutige Job-ID."""
    return uuid.uuid4().hex[:12]


@dataclass
class Workspace:
    """Kapselt die Pfade eines Jobs unter ``workspace/<job_id>/``."""

    job_id: str
    root: Path

    # --- Standard-Artefaktpfade ---
    @property
    def source_audio(self) -> Path:
        return self.root / "source.wav"

    @property
    def stems_dir(self) -> Path:
        return self.root / "stems"

    @property
    def blueprint_path(self) -> Path:
        return self.root / "blueprint.json"

    @property
    def report_path(self) -> Path:
        return self.root / "report.md"

    @property
    def lyrics_path(self) -> Path:
        return self.root / "lyrics.txt"

    @property
    def suno_request_path(self) -> Path:
        return self.root / "suno_request.json"

    @property
    def result_dir(self) -> Path:
        return self.root / "result"

    @property
    def status_path(self) -> Path:
        return self.root / "status.json"

    def ensure(self) -> "Workspace":
        """Legt das Workspace-Verzeichnis an."""
        self.root.mkdir(parents=True, exist_ok=True)
        return self

    # --- Status-Tracking (für UI-Polling) ---
    def write_status(self, stage: str, progress: int, message: str = "", **extra) -> None:
        data = {"stage": stage, "progress": progress, "message": message, **extra}
        self.status_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def read_status(self) -> dict:
        if not self.status_path.exists():
            return {"stage": "unknown", "progress": 0, "message": ""}
        return json.loads(self.status_path.read_text(encoding="utf-8"))


def get_workspace(job_id: str | None = None, *, create: bool = True) -> Workspace:
    """Liefert (und erstellt optional) den Workspace für eine Job-ID."""
    settings = get_settings()
    job_id = job_id or new_job_id()
    ws = Workspace(job_id=job_id, root=Path(settings.workspace_dir) / job_id)
    if create:
        ws.ensure()
    return ws
