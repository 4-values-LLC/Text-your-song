"""Struktur-Erkennung: Sektions-Grenzen + heuristische Labels.

Nutzt librosas Recurrence-/Agglomerative-Segmentierung, um Grenzen zu finden,
und labelt die Segmente anschließend heuristisch über Energie, Position und
Wiederholung (intro/verse/chorus/bridge/outro).
"""

from __future__ import annotations

import librosa
import numpy as np

from txtsong.models.blueprint import Section, SectionLabel, Structure


def _segment_boundaries(y: np.ndarray, sr: int, n_segments: int) -> np.ndarray:
    """Findet Segmentgrenzen (in Sekunden) via agglomerativer Clusterung."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    bounds = librosa.segment.agglomerative(chroma, n_segments)
    bound_times = librosa.frames_to_time(bounds, sr=sr)
    return bound_times


def _section_energy(y: np.ndarray, sr: int, start: float, end: float) -> float:
    a = int(start * sr)
    b = min(int(end * sr), len(y))
    if b <= a:
        return 0.0
    seg = y[a:b]
    return float(np.sqrt(np.mean(seg**2)))


def _chroma_signature(y: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    a = int(start * sr)
    b = min(int(end * sr), len(y))
    if b <= a:
        return np.zeros(12)
    chroma = librosa.feature.chroma_cqt(y=y[a:b], sr=sr)
    return chroma.mean(axis=1)


def detect_structure(
    y: np.ndarray, sr: int, duration: float, bpm: float | None = None
) -> Structure:
    """Erzeugt eine Struktur mit gelabelten Sektionen."""
    # Anzahl Segmente grob aus der Dauer ableiten (ca. alle 20 s eine Sektion).
    n_segments = int(np.clip(round(duration / 20), 4, 10))
    try:
        bounds = _segment_boundaries(y, sr, n_segments)
    except Exception:
        # Fallback: gleichmäßige Aufteilung.
        bounds = np.linspace(0, duration, n_segments + 1)

    # Grenzen säubern (0 und Ende einschließen, sortieren, deduplizieren).
    times = sorted({0.0, *[float(t) for t in bounds], float(duration)})
    spans = [(times[i], times[i + 1]) for i in range(len(times) - 1) if times[i + 1] - times[i] > 1.0]
    if not spans:
        spans = [(0.0, duration)]

    energies = [_section_energy(y, sr, s, e) for s, e in spans]
    max_e = max(energies) if energies else 1.0
    sigs = [_chroma_signature(y, sr, s, e) for s, e in spans]

    sec_per_bar = (60.0 / bpm) * 4 if bpm else None

    sections: list[Section] = []
    for i, ((start, end), energy, sig) in enumerate(zip(spans, energies, sigs)):
        norm_e = round(energy / (max_e + 1e-9), 3)
        label = _label_section(i, len(spans), norm_e, start, end, sig, sigs)
        bars = round((end - start) / sec_per_bar) if sec_per_bar else None
        sections.append(
            Section(
                index=i,
                label=label,
                start_s=round(start, 2),
                end_s=round(end, 2),
                bars=bars,
                energy=norm_e,
            )
        )

    form_summary = "-".join(s.label.value for s in sections)
    return Structure(sections=sections, form_summary=form_summary)


def _label_section(
    idx: int,
    total: int,
    norm_e: float,
    start: float,
    end: float,
    sig: np.ndarray,
    all_sigs: list[np.ndarray],
) -> SectionLabel:
    """Heuristisches Labeling über Position, Energie und Wiederholung."""
    is_first = idx == 0
    is_last = idx == total - 1

    # Wie oft ähnelt diese Sektion anderen? (hohe Wiederholung -> Chorus)
    similar = 0
    for j, other in enumerate(all_sigs):
        if j == idx:
            continue
        denom = (np.linalg.norm(sig) * np.linalg.norm(other)) + 1e-9
        cos = float(np.dot(sig, other) / denom)
        if cos > 0.9:
            similar += 1

    if is_first and norm_e < 0.5:
        return SectionLabel.INTRO
    if is_last and norm_e < 0.5:
        return SectionLabel.OUTRO
    # Stark wiederholte, energiereiche Sektion -> Chorus.
    if similar >= 1 and norm_e >= 0.6:
        return SectionLabel.CHORUS
    # Einmalige, mittlere Sektion in der zweiten Hälfte -> Bridge.
    if similar == 0 and 0.35 <= norm_e < 0.7 and idx >= total * 0.6:
        return SectionLabel.BRIDGE
    return SectionLabel.VERSE
