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


def test_style_instrumental_output(sample_blueprint: SongBlueprint):
    """instrumental=True -> 'instrumental' im Style, kein Vocal-Style."""
    style = build_style(sample_blueprint, instrumental=True).lower()
    assert "instrumental" in style
    assert "vocals" not in style
    assert "female" not in style


def test_style_adds_vocals_for_instrumental_source(sample_blueprint: SongBlueprint):
    """Quelle ohne Gesang, gewünschte Ausgabe MIT Gesang (Default).

    Kern-Regression: Der Style darf dann NICHT 'instrumental' sagen, sondern muss
    einen Vocal-Style ergänzen, da der Nutzer eigene Lyrics darüberlegt.
    """
    sample_blueprint.vocals.present = False
    sample_blueprint.vocals.gender_guess = None
    sample_blueprint.vocals.style = None
    style = build_style(sample_blueprint, instrumental=False).lower()
    assert "instrumental" not in style
    assert "vocals" in style  # Default-Vocal-Style ('lead vocals')


def test_derive_title(sample_blueprint: SongBlueprint):
    assert "Remix" in derive_title(sample_blueprint)


def test_vocal_gender(sample_blueprint: SongBlueprint):
    assert derive_vocal_gender(sample_blueprint) == "f"
