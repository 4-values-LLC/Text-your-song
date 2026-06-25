"""Hintergrund-Jobs: Analyse & Remix.

Unterstützt zwei Modi (per ``USE_QUEUE``):
- inline via FastAPI BackgroundTasks (Default, kein Redis nötig)
- RQ + Redis (robust, überlebt Neustarts)

Beide rufen dieselben Funktionen auf. Fehler werden in den Job-Status geschrieben,
damit die UI sie anzeigen kann.
"""

from __future__ import annotations

from txtsong.config import get_settings
from txtsong.pipeline import run_analysis, run_remix
from txtsong.utils.logging import get_logger
from txtsong.utils.workspace import get_workspace

log = get_logger(__name__)


def analysis_job(source_input: str, job_id: str) -> None:
    """Führt die Analyse aus und schreibt den Status (inkl. Fehler)."""
    ws = get_workspace(job_id)
    try:
        run_analysis(source_input, job_id=job_id)
    except Exception as exc:  # noqa: BLE001 - Fehler in Status spiegeln
        log.exception("Analyse-Job %s fehlgeschlagen", job_id)
        ws.write_status("error", 100, f"Analyse fehlgeschlagen: {exc}")


def remix_job(job_id: str, user_lyrics: str, instrumental: bool = False) -> None:
    """Führt den Remix aus und schreibt den Status (inkl. Fehler)."""
    ws = get_workspace(job_id, create=False)
    try:
        run_remix(job_id, user_lyrics, instrumental=instrumental)
    except Exception as exc:  # noqa: BLE001
        log.exception("Remix-Job %s fehlgeschlagen", job_id)
        ws.write_status("error", 100, f"Remix fehlgeschlagen: {exc}")


def _enqueue(func, *args) -> None:
    """Stellt einen Job in die RQ-Queue (nur bei USE_QUEUE)."""
    from redis import Redis
    from rq import Queue

    settings = get_settings()
    queue = Queue(connection=Redis.from_url(settings.redis_url))
    queue.enqueue(func, *args, job_timeout=1800)


def dispatch_analysis(source_input: str, job_id: str, background_tasks=None) -> None:
    """Startet den Analyse-Job (Queue oder inline)."""
    settings = get_settings()
    if settings.use_queue:
        _enqueue(analysis_job, source_input, job_id)
    elif background_tasks is not None:
        background_tasks.add_task(analysis_job, source_input, job_id)
    else:
        analysis_job(source_input, job_id)


def dispatch_remix(
    job_id: str, user_lyrics: str, *, instrumental: bool = False, background_tasks=None
) -> None:
    """Startet den Remix-Job (Queue oder inline)."""
    settings = get_settings()
    if settings.use_queue:
        _enqueue(remix_job, job_id, user_lyrics, instrumental)
    elif background_tasks is not None:
        background_tasks.add_task(remix_job, job_id, user_lyrics, instrumental)
    else:
        remix_job(job_id, user_lyrics, instrumental)
