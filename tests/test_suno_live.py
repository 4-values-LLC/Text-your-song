"""Echte End-to-End-Tests gegen die Suno-API (sunoapi.org).

Diese Tests rufen **wirklich** das Netzwerk auf, brauchen einen gültigen
``SUNO_API_KEY`` und sind deshalb mit ``@pytest.mark.live`` markiert. Sie werden
durch die Default-``addopts`` (``-m 'not slow and not live'``) **immer
übersprungen** und zusätzlich per Umgebungsvariable scharf geschaltet:

- ``RUN_SUNO_LIVE=1``  -> aktiviert den **Upload-Test** (kostenlos, keine Credits).
- ``RUN_SUNO_LIVE_COVER=1`` -> aktiviert den **vollen Cover/Remix-Test**
  (verbraucht Suno-Credits, dauert mehrere Minuten).

Ausführen:

    RUN_SUNO_LIVE=1 SUNO_API_KEY=... pytest -m live -s tests/test_suno_live.py
    RUN_SUNO_LIVE_COVER=1 SUNO_API_KEY=... pytest -m live -s tests/test_suno_live.py

Optionale Env-Schalter für den Cover-Test:
- ``SUNO_LIVE_VOCAL=1``        -> Vocal-Remix mit Mini-Lyrics statt instrumental.
- ``SUNO_LIVE_TIMEOUT=600``    -> Poll-Timeout in Sekunden (Default 420).
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import numpy as np
import pytest
import soundfile as sf

from txtsong.config import get_settings
from txtsong.models.suno import SunoRequest
from txtsong.suno.client import SunoClient, validate_request
from txtsong.suno.poller import fetch_results, poll_until_complete
from txtsong.suno.upload import upload_audio

pytestmark = pytest.mark.live


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_key() -> str:
    key = get_settings().suno_api_key
    if not key:
        pytest.skip("SUNO_API_KEY ist nicht gesetzt.")
    return key


# --------------------------------------------------------------------------- #
# Synthetische, lizenzfreie Test-Audiodatei                                    #
# --------------------------------------------------------------------------- #
def _write_synthetic_wav(dst: Path, *, seconds: float = 25.0, sr: int = 44100) -> Path:
    """Erzeugt eine kurze, gut analysierbare Stereo-WAV (Akkord + Beat).

    Lizenzfrei (selbst generiert) -> als Cover-Quelle für Suno geeignet.
    """
    t = np.linspace(0.0, seconds, int(seconds * sr), endpoint=False)

    # A-Moll-Akkord (A2, C4, E4) als harmonische Basis.
    chord = sum(0.18 * np.sin(2 * np.pi * f * t) for f in (110.0, 261.63, 329.63))

    # Vier-Viertel-Beat bei 120 BPM (Klick alle 0.5 s) für klares Tempo.
    beat = np.zeros_like(t)
    click_len = int(0.04 * sr)
    for k in range(int(seconds / 0.5)):
        start = int(k * 0.5 * sr)
        env = np.exp(-np.linspace(0, 8, click_len))
        beat[start:start + click_len] += 0.5 * env * np.sin(
            2 * np.pi * 1800.0 * t[:click_len]
        )

    mono = chord + beat
    mono /= np.max(np.abs(mono)) + 1e-9  # normalisieren
    stereo = np.column_stack([mono, mono]).astype(np.float32)

    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(dst, stereo, sr)
    return dst


@pytest.fixture
def synthetic_wav(tmp_path: Path) -> Path:
    return _write_synthetic_wav(tmp_path / "source.wav")


# --------------------------------------------------------------------------- #
# Test 1: echter Datei-Upload (kostenlos)                                      #
# --------------------------------------------------------------------------- #
def test_live_upload(synthetic_wav: Path):
    """Lädt eine echte WAV zum Suno-File-Host und prüft die downloadUrl."""
    if not _flag("RUN_SUNO_LIVE"):
        pytest.skip("RUN_SUNO_LIVE nicht gesetzt.")
    _require_key()

    url = upload_audio(synthetic_wav)
    assert url.startswith("http"), f"Unerwartete Upload-URL: {url}"

    # Die URL muss öffentlich abrufbar sein (geht 1:1 als uploadUrl in Cover).
    resp = httpx.get(url, timeout=60, follow_redirects=True)
    assert resp.status_code == 200, f"downloadUrl nicht abrufbar: {resp.status_code}"
    assert len(resp.content) > 1000, "Heruntergeladene Datei verdächtig klein."


# --------------------------------------------------------------------------- #
# Test 2: voller Cover/Remix end-to-end (verbraucht Credits, dauert Minuten)   #
# --------------------------------------------------------------------------- #
def test_live_cover_end_to_end(synthetic_wav: Path, tmp_path: Path):
    """Upload -> upload-cover -> Polling bis complete -> Track-Download.

    Deckt den echten Pfad aus ``pipeline.run_remix`` ab, ohne Analyse/Blueprint
    (Style/Title werden direkt gesetzt). Standard: instrumentaler Remix; mit
    ``SUNO_LIVE_VOCAL=1`` ein Vocal-Remix mit Mini-Lyrics.
    """
    if not _flag("RUN_SUNO_LIVE_COVER"):
        pytest.skip("RUN_SUNO_LIVE_COVER nicht gesetzt.")
    _require_key()

    settings = get_settings()
    vocal = _flag("SUNO_LIVE_VOCAL")
    timeout_s = float(os.getenv("SUNO_LIVE_TIMEOUT", "420"))

    # 1) Audio hochladen -> öffentliche URL.
    upload_url = upload_audio(synthetic_wav)

    # 2) Request bauen (Pre-Flight-validiert, wie in der echten Pipeline).
    if vocal:
        prompt = "[Verse]\nthis is a live test\nsinging just a line\n\n[Chorus]\nremix in the night"
    else:
        prompt = ""
    req = SunoRequest(
        upload_url=upload_url,
        style="ambient electronic, 120 BPM, A minor, calm"
        + ("" if vocal else ", instrumental"),
        title="Live Test Remix",
        prompt=prompt,
        model=settings.suno_model,
        custom_mode=True,
        instrumental=not vocal,
        callback_url=settings.suno_callback_url or None,
        audio_weight=settings.suno_audio_weight,
        style_weight=settings.suno_style_weight,
        weirdness_constraint=settings.suno_weirdness,
    )
    validate_request(req)  # darf nicht werfen

    # 3) Cover absenden -> taskId.
    client = SunoClient()
    task_id = client.submit_cover(req)
    assert task_id, "Keine taskId von Suno erhalten."
    print(f"\nSuno-Task gestartet: {task_id}")

    # 4) Pollen bis complete (mit Status-Ausgabe).
    result = poll_until_complete(
        client,
        task_id,
        interval_s=15.0,
        timeout_s=timeout_s,
        on_update=lambda r: print(f"  Status: {r.status}"),
    )
    assert result.status == "complete"
    assert result.tracks, "Ergebnis ohne Tracks."

    # 5) Tracks herunterladen und prüfen.
    out_dir = tmp_path / "result"
    fetch_results(client, result, out_dir)
    downloaded = [Path(t.local_path) for t in result.tracks if t.local_path]
    assert downloaded, "Kein Track heruntergeladen."
    for p in downloaded:
        assert p.exists() and p.stat().st_size > 10_000, f"Track zu klein: {p}"
        print(f"  Remix gespeichert: {p} ({p.stat().st_size} Bytes)")
