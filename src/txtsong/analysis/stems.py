"""Stem-Trennung mit Demucs + abgeleitete Instrumentierung.

Trennt die Quelle in vocals/drums/bass/other und leitet aus der relativen
Energie je Stem die Instrumentierung, Drum-Dichte, Bass-Präsenz und
Vocal-Präsenz/Gender ab.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from txtsong.config import get_settings
from txtsong.models.blueprint import Instrumentation, SongBlueprint
from txtsong.utils.logging import get_logger

log = get_logger(__name__)

STEM_NAMES = ["vocals", "drums", "bass", "other"]


def _run_demucs(audio_path: Path, out_dir: Path, model: str) -> dict[str, Path]:
    """Ruft Demucs als Subprozess auf und gibt die Pfade der Stems zurück."""
    import subprocess

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python", "-m", "demucs",
        "-n", model,
        "-o", str(out_dir),
        str(audio_path),
    ]
    log.info("Starte Demucs (%s) ...", model)
    subprocess.run(cmd, check=True, capture_output=True)
    # Demucs legt out_dir/<model>/<track_name>/<stem>.wav an.
    track_dir = out_dir / model / audio_path.stem
    return {name: track_dir / f"{name}.wav" for name in STEM_NAMES}


def _stem_energy(path: Path) -> float:
    if not path.exists():
        return 0.0
    y, _ = librosa.load(str(path), sr=None, mono=True)
    return float(np.sqrt(np.mean(y**2))) if y.size else 0.0


def _guess_vocal_gender(vocal_path: Path) -> str | None:
    """Schätzt das Vocal-Geschlecht über die mittlere Grundfrequenz (F0)."""
    if not vocal_path.exists():
        return None
    y, sr = librosa.load(str(vocal_path), sr=None, mono=True)
    if y.size == 0:
        return None
    try:
        f0, voiced, _ = librosa.pyin(
            y, fmin=65, fmax=400, sr=sr, frame_length=2048
        )
    except Exception:
        return None
    f0 = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    if f0.size == 0:
        return None
    median_f0 = float(np.median(f0))
    # Grobe Schwelle: ~165 Hz trennt typische m/f-Sprechgrundfrequenzen.
    return "m" if median_f0 < 165 else "f"


def _density(value: float, lo: float, hi: float) -> str:
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "medium"


def analyze_stems(ws, blueprint: SongBlueprint) -> None:
    """Führt Demucs aus und reichert den Blueprint mit Instrumentierung/Vocals an."""
    settings = get_settings()
    stems = _run_demucs(ws.source_audio, ws.stems_dir, settings.demucs_model)

    energies = {name: _stem_energy(path) for name, path in stems.items()}
    total = sum(energies.values()) + 1e-9
    rel = {name: round(e / total, 3) for name, e in energies.items()}

    detected = [name for name, e in energies.items() if e > 0.005]

    instruments: list[str] = []
    if rel.get("drums", 0) > 0.15:
        instruments.append("drums")
    if rel.get("bass", 0) > 0.1:
        instruments.append("bass")
    if rel.get("other", 0) > 0.2:
        instruments.append("harmonic instruments (synths/guitars/keys)")

    blueprint.instrumentation = Instrumentation(
        stems_detected=detected,
        stem_energy=rel,
        instruments=instruments,
        drum_density=_density(rel.get("drums", 0), 0.12, 0.3),
        bass_prominence=_density(rel.get("bass", 0), 0.08, 0.2),
    )

    # Vocal-Präsenz & Gender.
    vocal_energy = rel.get("vocals", 0)
    blueprint.vocals.present = vocal_energy > 0.05
    if blueprint.vocals.present:
        blueprint.vocals.gender_guess = _guess_vocal_gender(stems["vocals"])
