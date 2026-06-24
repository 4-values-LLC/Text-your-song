# 🎵 Text Your Song

Analysiert einen Song **wie ein Musikproduzent** und produziert ihn über die
[Suno-API](https://sunoapi.org) als **Remix mit deinem eigenen Text** neu.

Du gibst einen **YouTube-/Spotify-Link** oder eine **Audiodatei** an – die App
zerlegt den Song in alle relevanten Bestandteile (Tempo, Tonart, Struktur,
Instrumentierung, Vocals, Stimmung, Produktion), erstellt einen verständlichen
Producer-Report und ein optimal aufbereitetes Suno-Paket. Anschließend wird der
Song mit deinem Text als Remix neu erzeugt.

## Wie es funktioniert

```
Song-Link/Datei
   │
   ▼
[A] Ingest        yt-dlp / Datei / Spotify→YouTube  ──► source.wav
[B] Analyse       librosa (BPM, Tonart, Struktur, Energie, Klang)
                  Demucs (Stems → Instrumentierung, Vocal-Gender)
                  Whisper (Originaltext + Zeilen je Sektion)        ──► blueprint.json
[C] Report        deutscher Producer-Report                         ──► report.md
[D] Prompt        Style (EN) + getaggte Lyric-Vorlage + dein Text   ──► suno_request.json
[E] Suno          Upload → upload-cover → Polling → Download         ──► result/remix_*.mp3
```

Das zentrale Artefakt ist der **`SongBlueprint`** (`src/txtsong/models/blueprint.py`) –
ein vollständiges, strukturiertes Abbild des Songs, das Report, Style-Builder und
Lyric-Vorlage speist.

## Voraussetzungen

- Python 3.11+
- **ffmpeg** (für yt-dlp, librosa, Demucs) im PATH
- Ein **Suno-API-Key** von [sunoapi.org](https://sunoapi.org)
- Für die volle Analyse: ausreichend RAM (Demucs/Whisper, idealerweise GPU)

> Hinweis: Demucs/Whisper/torch + ffmpeg brauchen einen **echten Server** –
> nicht Serverless (Vercel o. ä.). Nutze Docker oder einen VPS/GPU-Host.

## Schnellstart (Docker, empfohlen)

```bash
cp .env.example .env        # SUNO_API_KEY eintragen
docker compose up --build
# → http://localhost:8000
```

## Lokal (ohne Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-heavy.txt      # Demucs/Whisper (optional, schwer)
pip install -e .
cp .env.example .env                        # SUNO_API_KEY eintragen

# Web-App (Jobs laufen inline, kein Redis nötig: USE_QUEUE=false)
uvicorn webapp.main:app --reload
```

Ohne die schweren Pakete läuft die Analyse weiterhin (librosa-only); Demucs/Whisper
werden dann automatisch übersprungen (`DEMUCS_ENABLED`/`WHISPER_ENABLED`).

## CLI

```bash
# Nur analysieren (Report + Lyric-Vorlage)
python -m txtsong.cli analyze "https://www.youtube.com/watch?v=..."

# Remix für einen analysierten Job (Dry-Run baut nur den Request)
python -m txtsong.cli remix <job_id> --lyrics mein_text.txt --dry-run

# Alles in einem Schritt
python -m txtsong.cli run song.mp3 --lyrics mein_text.txt
```

## Konfiguration (`.env`)

| Variable | Bedeutung | Default |
|----------|-----------|---------|
| `SUNO_API_KEY` | API-Key von sunoapi.org | – |
| `SUNO_MODEL` | `V4_5PLUS`, `V5`, `V5_5` … | `V4_5PLUS` |
| `SUNO_AUDIO_WEIGHT` | Einfluss des Original-Audios (0–1) | `0.65` |
| `DEMUCS_ENABLED` / `WHISPER_ENABLED` | volle Analyse an/aus | `true` |
| `USE_QUEUE` | RQ+Redis statt Inline-Jobs | `false` |

## Tests

```bash
pip install -e ".[dev]"
pytest            # schnelle Unit-Tests (ohne schwere ML-Deps)
pytest -m slow    # zusätzlich Demucs/Whisper-Tests
```

## Projektstruktur

```
src/txtsong/        Pipeline-Paket (auch ohne Web nutzbar)
  models/           SongBlueprint, SunoRequest, Lyrics (Pydantic-Schemas)
  ingest/           youtube · local · spotify
  analysis/         features (librosa) · stems (Demucs) · transcribe (Whisper) · blueprint
  report/           producer_report (Deutsch)
  prompt/           style_builder · lyrics_template · lyric_aligner
  suno/             upload · client · poller
  pipeline.py       Orchestrator   ·   cli.py   CLI
webapp/             FastAPI + Jinja2/HTMX (main, jobs, templates, static)
tests/              Unit-Tests
```

## Rechtlicher Hinweis

Verarbeite nur Songs, für die du die nötigen Rechte hast. Diese Anwendung dient
dazu, **eigene** Songs/Ideen mit eigenem Text neu zu produzieren.
