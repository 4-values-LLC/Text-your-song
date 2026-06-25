"""Low-Level-Audio-Analyse mit librosa.

Liefert Tempo/BPM, Tonart (Krumhansl-Schmuckler-Korrelation über Chroma),
Energie-/Lautheits-Kennwerte und spektrale Merkmale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import librosa
import numpy as np

# Krumhansl-Schmuckler Key-Profile (Dur/Moll).
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class AudioFeatures:
    y: np.ndarray
    sr: int
    duration_s: float
    bpm: float
    bpm_confidence: float
    beat_times: list[float]
    tempo_stability: str
    key: str
    scale: str
    key_confidence: float
    rms_mean: float
    rms_peak: float
    loudness_lufs_est: float
    dynamic_range: str
    centroid_hz: float
    rolloff_hz: float
    brightness: str
    energy_curve: list[float] = field(default_factory=list)


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, str, float]:
    """Tonart über Korrelation des mittleren Chroma-Vektors mit Key-Profilen."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    if chroma_mean.sum() > 0:
        chroma_mean = chroma_mean / chroma_mean.sum()

    best_corr = -np.inf
    best_key = "C"
    best_scale = "major"
    runner_up = -np.inf
    for i in range(12):
        for profile, scale in ((_MAJOR_PROFILE, "major"), (_MINOR_PROFILE, "minor")):
            rotated = np.roll(profile, i)
            corr = float(np.corrcoef(chroma_mean, rotated)[0, 1])
            if np.isnan(corr):
                continue
            if corr > best_corr:
                runner_up = best_corr
                best_corr = corr
                best_key = _PITCH_CLASSES[i]
                best_scale = scale
            elif corr > runner_up:
                runner_up = corr
    # Confidence: Abstand zum zweitbesten Kandidaten, auf 0–1 normiert.
    confidence = float(np.clip((best_corr - max(runner_up, 0)) * 2, 0, 1))
    return best_key, best_scale, round(confidence, 3)


def _estimate_lufs(rms_mean: float) -> float:
    """Grobe LUFS-Schätzung aus dem mittleren RMS (kein echtes ITU-BS.1770)."""
    if rms_mean <= 0:
        return -70.0
    return round(20 * float(np.log10(rms_mean)) - 3.0, 1)


def _classify_dynamic_range(rms: np.ndarray) -> str:
    if rms.size == 0:
        return "moderate"
    crest = float(np.max(rms) / (np.mean(rms) + 1e-9))
    if crest < 1.6:
        return "compressed"
    if crest > 2.6:
        return "wide"
    return "moderate"


def extract_features(audio_path: str) -> AudioFeatures:
    """Komplette librosa-Analyse einer Audiodatei."""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    # --- Tempo & Beats ---
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
    # Stabilität: Streuung der Inter-Beat-Intervalle.
    if len(beat_times) > 2:
        intervals = np.diff(beat_times)
        cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9))
        tempo_stability = "steady" if cv < 0.12 else "variable"
        bpm_confidence = float(np.clip(1.0 - cv, 0, 1))
    else:
        tempo_stability = "variable"
        bpm_confidence = 0.3

    # --- Tonart ---
    key, scale, key_conf = _detect_key(y, sr)

    # --- Lautheit / Dynamik ---
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(np.mean(rms))
    rms_peak = float(np.max(rms)) if rms.size else 0.0
    loudness = _estimate_lufs(rms_mean)
    dyn_range = _classify_dynamic_range(rms)

    # --- Spektrum / Helligkeit ---
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    if centroid < 1500:
        brightness = "dark"
    elif centroid > 3000:
        brightness = "bright"
    else:
        brightness = "balanced"

    # --- Energie-Verlauf (auf ~64 Stützstellen reduziert) ---
    if rms.size:
        n = min(64, rms.size)
        idx = np.linspace(0, rms.size - 1, n).astype(int)
        curve = rms[idx]
        curve = (curve - curve.min()) / (np.ptp(curve) + 1e-9)
        energy_curve = [round(float(v), 3) for v in curve]
    else:
        energy_curve = []

    return AudioFeatures(
        y=y,
        sr=sr,
        duration_s=duration,
        bpm=round(bpm, 1),
        bpm_confidence=round(bpm_confidence, 3),
        beat_times=[round(t, 3) for t in beat_times],
        tempo_stability=tempo_stability,
        key=key,
        scale=scale,
        key_confidence=key_conf,
        rms_mean=rms_mean,
        rms_peak=round(rms_peak, 4),
        loudness_lufs_est=loudness,
        dynamic_range=dyn_range,
        centroid_hz=round(centroid, 1),
        rolloff_hz=round(rolloff, 1),
        brightness=brightness,
        energy_curve=energy_curve,
    )
