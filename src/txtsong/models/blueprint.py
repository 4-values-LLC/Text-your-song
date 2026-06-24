"""SongBlueprint – die strukturierte, vollständige Producer-Analyse eines Songs.

Dieses Schema ist das zentrale Artefakt der Pipeline: Es wird von der Analyse
erzeugt und vom Report, Style-Builder und Lyric-Template konsumiert. Jedes Feld
ist nullbar, damit ein Blueprint auch dann gültig ist, wenn ein Analyzer
(z. B. Demucs oder Whisper) übersprungen wurde.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class SectionLabel(str, Enum):
    """Mögliche Sektions-Typen einer Songstruktur."""

    INTRO = "intro"
    VERSE = "verse"
    PRECHORUS = "prechorus"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    DROP = "drop"
    BREAKDOWN = "breakdown"
    OUTRO = "outro"
    INSTRUMENTAL = "instrumental"


class Source(BaseModel):
    origin: Literal["youtube", "spotify", "local"] = "local"
    url: str | None = None
    title: str | None = None
    artist: str | None = None
    duration_s: float | None = None
    sample_rate: int | None = None


class Tempo(BaseModel):
    bpm: float | None = None
    bpm_confidence: float | None = None
    time_signature: str | None = None  # z. B. "4/4"
    tempo_stability: Literal["steady", "variable"] | None = None
    # Beat-Zeitpunkte können sehr lang sein -> im Report ausgeblendet.
    beat_times_s: list[float] = Field(default_factory=list)


class Tonality(BaseModel):
    key: str | None = None  # z. B. "A"
    scale: Literal["major", "minor"] | None = None
    key_confidence: float | None = None
    mode_notes: str | None = None


class Section(BaseModel):
    index: int
    label: SectionLabel
    start_s: float
    end_s: float
    bars: int | None = None
    energy: float | None = None  # normalisiert 0–1
    lyric_lines: int | None = None  # aus Whisper, sonst None
    notes: str | None = None

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_s - self.start_s)


class Structure(BaseModel):
    sections: list[Section] = Field(default_factory=list)
    form_summary: str | None = None  # z. B. "Intro-Verse-Chorus-Verse-Chorus-Outro"


class Instrumentation(BaseModel):
    stems_detected: list[str] = Field(default_factory=list)
    stem_energy: dict[str, float] = Field(default_factory=dict)
    instruments: list[str] = Field(default_factory=list)  # abgeleitet/heuristisch
    drum_density: Literal["low", "medium", "high"] | None = None
    bass_prominence: Literal["low", "medium", "high"] | None = None


class Vocals(BaseModel):
    present: bool | None = None
    gender_guess: Literal["m", "f"] | None = None
    style: str | None = None
    vocal_register: str | None = None
    lyrics_transcribed: str | None = None
    language: str | None = None


class Dynamics(BaseModel):
    energy_curve: list[float] = Field(default_factory=list)
    loudness_lufs_est: float | None = None
    rms_peak: float | None = None
    dynamic_range: Literal["compressed", "moderate", "wide"] | None = None


class Spectral(BaseModel):
    centroid_hz_mean: float | None = None
    brightness: Literal["dark", "balanced", "bright"] | None = None
    rolloff_hz: float | None = None


class Production(BaseModel):
    genre: str | None = None
    subgenre: str | None = None
    mood: list[str] = Field(default_factory=list)
    era: str | None = None
    production_notes: str | None = None


class AnalysisMeta(BaseModel):
    demucs_used: bool = False
    whisper_used: bool = False
    generated_at: str | None = None  # ISO-8601
    librosa_version: str | None = None


class SongBlueprint(BaseModel):
    """Vollständige analytische Beschreibung eines Songs."""

    schema_version: str = SCHEMA_VERSION
    source: Source = Field(default_factory=Source)
    tempo: Tempo = Field(default_factory=Tempo)
    tonality: Tonality = Field(default_factory=Tonality)
    structure: Structure = Field(default_factory=Structure)
    instrumentation: Instrumentation = Field(default_factory=Instrumentation)
    vocals: Vocals = Field(default_factory=Vocals)
    dynamics: Dynamics = Field(default_factory=Dynamics)
    spectral: Spectral = Field(default_factory=Spectral)
    production: Production = Field(default_factory=Production)
    analysis_meta: AnalysisMeta = Field(default_factory=AnalysisMeta)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, data: str) -> "SongBlueprint":
        return cls.model_validate_json(data)
