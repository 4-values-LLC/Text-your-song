"""Gemeinsame Fixtures."""

from __future__ import annotations

import pytest

from txtsong.models.blueprint import (
    Instrumentation,
    Production,
    Section,
    SectionLabel,
    SongBlueprint,
    Source,
    Spectral,
    Tempo,
    Tonality,
    Vocals,
)


@pytest.fixture
def sample_blueprint() -> SongBlueprint:
    """Ein realistischer Blueprint für Prompt-/Report-Tests."""
    return SongBlueprint(
        source=Source(origin="youtube", title="Test Song", artist="Tester", duration_s=180.0),
        tempo=Tempo(bpm=128.0, bpm_confidence=0.82, time_signature="4/4", tempo_stability="steady"),
        tonality=Tonality(key="A", scale="minor", key_confidence=0.74),
        production=Production(
            genre="electronic / dance", subgenre="edm", mood=["energetic", "uplifting"], era="2010s"
        ),
        instrumentation=Instrumentation(
            stems_detected=["vocals", "drums", "bass", "other"],
            instruments=["drums", "bass", "harmonic instruments (synths/guitars/keys)"],
            drum_density="high",
            bass_prominence="high",
        ),
        vocals=Vocals(present=True, gender_guess="f", style="breathy pop"),
        spectral=Spectral(brightness="bright", centroid_hz_mean=2500.0),
    )


@pytest.fixture
def blueprint_with_structure(sample_blueprint: SongBlueprint) -> SongBlueprint:
    """Blueprint mit einer Intro-Verse-Chorus-Verse-Chorus-Outro-Struktur."""
    labels = [
        SectionLabel.INTRO,
        SectionLabel.VERSE,
        SectionLabel.CHORUS,
        SectionLabel.VERSE,
        SectionLabel.CHORUS,
        SectionLabel.OUTRO,
    ]
    sections = []
    t = 0.0
    for i, label in enumerate(labels):
        sections.append(
            Section(index=i, label=label, start_s=t, end_s=t + 30, bars=8, energy=0.5)
        )
        t += 30
    sample_blueprint.structure.sections = sections
    sample_blueprint.structure.form_summary = "-".join(l.value for l in labels)
    return sample_blueprint
