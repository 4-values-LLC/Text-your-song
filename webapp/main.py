"""FastAPI-App: Upload/Link -> Analyse -> Report -> Text -> Remix -> Download."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from txtsong.models.blueprint import SongBlueprint
from txtsong.prompt.lyrics_template import build_template, template_as_text
from txtsong.report import render_report
from txtsong.utils.workspace import get_workspace, new_job_id
from webapp.jobs import dispatch_analysis, dispatch_remix

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Text Your Song")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze(
    request: Request,
    background_tasks: BackgroundTasks,
    source_url: str = Form(""),
    audio_file: UploadFile | None = None,
):
    """Startet einen Analyse-Job aus URL oder Datei-Upload."""
    job_id = new_job_id()
    ws = get_workspace(job_id)

    if audio_file is not None and audio_file.filename:
        upload_path = ws.root / f"upload_{audio_file.filename}"
        with open(upload_path, "wb") as fh:
            shutil.copyfileobj(audio_file.file, fh)
        source_input = str(upload_path)
    elif source_url.strip():
        source_input = source_url.strip()
    else:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "Bitte einen Link angeben oder eine Datei hochladen."},
            status_code=400,
        )

    ws.write_status("queued", 0, "Job eingereiht ...")
    dispatch_analysis(source_input, job_id, background_tasks)
    return RedirectResponse(url=f"/job/{job_id}", status_code=303)


@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str):
    """Fortschrittsseite der Analyse (pollt /job/{id}/status via HTMX)."""
    return templates.TemplateResponse(
        "analyzing.html", {"request": request, "job_id": job_id}
    )


@app.get("/job/{job_id}/status", response_class=HTMLResponse)
def job_status(request: Request, job_id: str):
    """HTMX-Fragment: aktueller Analyse-Status."""
    ws = get_workspace(job_id, create=False)
    status = ws.read_status()
    # Bei Abschluss/Fehler signalisiert das Template den Redirect.
    done = status.get("stage") == "done_analysis"
    error = status.get("stage") == "error"
    return templates.TemplateResponse(
        "_status.html",
        {
            "request": request,
            "job_id": job_id,
            "status": status,
            "done": done,
            "error": error,
            "redirect": f"/job/{job_id}/result" if done else None,
        },
    )


@app.get("/job/{job_id}/result", response_class=HTMLResponse)
def result_page(request: Request, job_id: str):
    """Ergebnis-Seite: Report + Struktur + Lyric-Vorlage + Text-Formular."""
    ws = get_workspace(job_id, create=False)
    bp = SongBlueprint.from_json(ws.blueprint_path.read_text(encoding="utf-8"))
    report_md = ws.report_path.read_text(encoding="utf-8") if ws.report_path.exists() else render_report(bp)
    template_text = template_as_text(build_template(bp))
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_id": job_id,
            "blueprint": bp,
            "report_md": report_md,
            "template_text": template_text,
        },
    )


@app.post("/job/{job_id}/remix")
def start_remix(
    request: Request,
    job_id: str,
    background_tasks: BackgroundTasks,
    lyrics: str = Form(...),
):
    """Startet den Remix-Job mit dem eigenen Text des Nutzers."""
    ws = get_workspace(job_id, create=False)
    ws.write_status("queued", 0, "Remix eingereiht ...")
    dispatch_remix(job_id, lyrics, background_tasks)
    return RedirectResponse(url=f"/job/{job_id}/remixing", status_code=303)


@app.get("/job/{job_id}/remixing", response_class=HTMLResponse)
def remixing_page(request: Request, job_id: str):
    return templates.TemplateResponse(
        "remixing.html", {"request": request, "job_id": job_id}
    )


@app.get("/job/{job_id}/remix-status", response_class=HTMLResponse)
def remix_status(request: Request, job_id: str):
    """HTMX-Fragment: aktueller Remix-Status."""
    ws = get_workspace(job_id, create=False)
    status = ws.read_status()
    done = status.get("stage") == "done"
    error = status.get("stage") == "error"
    return templates.TemplateResponse(
        "_status.html",
        {
            "request": request,
            "job_id": job_id,
            "status": status,
            "done": done,
            "error": error,
            "redirect": f"/job/{job_id}/done" if done else None,
        },
    )


@app.get("/job/{job_id}/done", response_class=HTMLResponse)
def done_page(request: Request, job_id: str):
    """Fertig-Seite: Audio-Player + Download der Remix-Tracks."""
    ws = get_workspace(job_id, create=False)
    tracks = sorted(ws.result_dir.glob("*.mp3")) if ws.result_dir.exists() else []
    track_names = [t.name for t in tracks]
    return templates.TemplateResponse(
        "done.html",
        {"request": request, "job_id": job_id, "tracks": track_names},
    )


@app.get("/job/{job_id}/media/{filename}")
def media(job_id: str, filename: str):
    """Liefert eine Audio-Ergebnisdatei aus."""
    ws = get_workspace(job_id, create=False)
    path = (ws.result_dir / filename).resolve()
    # Pfad-Traversal verhindern.
    if ws.result_dir.resolve() not in path.parents:
        return HTMLResponse("Ungültiger Pfad", status_code=400)
    if not path.exists():
        return HTMLResponse("Datei nicht gefunden", status_code=404)
    return FileResponse(path, media_type="audio/mpeg", filename=filename)
