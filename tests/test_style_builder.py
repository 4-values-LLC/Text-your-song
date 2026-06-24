"""Tests für den Style-Builder (Suno-Style-String)."""

from __future__ import annotations

from txtsong.models.blueprint import SongBlueprint
from txtsong.prompt.style_builder import build_style, derive_title, derive_vocal_gender


def test_style_contains_core_descriptors(sample_blueprint: SongBlueprint):
    style = build_style(sample_blueprint)
    assert "128 BPM" in style
    assert "A minor" in style
    assert "edm" in style.lower()
    assert "female" in style.lower()
    assert "2010s production" in style


def test_style_respects_max_len(sample_blueprint: SongBlueprint):
    style = build_style(sample_blueprint, max_len=30)
    assert len(style) <= 30


def test_style_dedupes(sample_blueprint: SongBlueprint):
    style = build_style(sample_blueprint)
    parts = [p.strip().lower() for p in style.split(",")]
    assert len(parts) == len(set(parts))


def test_derive_title(sample_blueprint: SongBlueprint):
    assert "Remix" in derive_title(sample_blueprint)


def test_vocal_gender(sample_blueprint: SongBlueprint):
    assert derive_vocal_gender(sample_blueprint) == "f"
