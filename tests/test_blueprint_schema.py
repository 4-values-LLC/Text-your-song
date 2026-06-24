"""Tests für das SongBlueprint-Schema (Roundtrip & Defaults)."""

from __future__ import annotations

from txtsong.models.blueprint import SongBlueprint


def test_empty_blueprint_is_valid():
    bp = SongBlueprint()
    assert bp.schema_version == "1.0"
    assert bp.source.origin == "local"
    assert bp.tempo.bpm is None


def test_json_roundtrip(sample_blueprint: SongBlueprint):
    data = sample_blueprint.to_json()
    restored = SongBlueprint.from_json(data)
    assert restored == sample_blueprint
    assert restored.tempo.bpm == 128.0
    assert restored.tonality.key == "A"


def test_section_duration(blueprint_with_structure: SongBlueprint):
    first = blueprint_with_structure.structure.sections[0]
    assert first.duration_s == 30.0
