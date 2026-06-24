"""Pydantic-Schemas – die Verträge zwischen den Pipeline-Stufen."""

from txtsong.models.blueprint import (
    SongBlueprint,
    Source,
    Tempo,
    Tonality,
    Structure,
    Section,
    Instrumentation,
    Vocals,
    Dynamics,
    Spectral,
    Production,
    AnalysisMeta,
)
from txtsong.models.lyrics import AlignedLyrics, LyricSection
from txtsong.models.suno import CoverResult, SunoRequest, SunoTrack

__all__ = [
    "SongBlueprint",
    "Source",
    "Tempo",
    "Tonality",
    "Structure",
    "Section",
    "Instrumentation",
    "Vocals",
    "Dynamics",
    "Spectral",
    "Production",
    "AnalysisMeta",
    "AlignedLyrics",
    "LyricSection",
    "SunoRequest",
    "SunoTrack",
    "CoverResult",
]
