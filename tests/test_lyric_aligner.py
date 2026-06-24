"""Tests für Lyric-Template & -Alignment (Chorus-Reuse, Mapping, Clamp)."""

from __future__ import annotations

from txtsong.models.blueprint import SongBlueprint
from txtsong.prompt.lyric_aligner import align_lyrics, clamp_prompt
from txtsong.prompt.lyrics_template import build_template


def test_template_marks_repeated_chorus(blueprint_with_structure: SongBlueprint):
    template = build_template(blueprint_with_structure)
    chorus_sections = [s for s in template.sections if s.tag == "[Chorus]"]
    assert len(chorus_sections) == 2
    # Der zweite Chorus referenziert den ersten.
    assert chorus_sections[0].repeat_of is None
    assert chorus_sections[1].repeat_of is not None


def test_freeform_mapping_and_chorus_reuse(blueprint_with_structure: SongBlueprint):
    template = build_template(blueprint_with_structure)
    user_text = (
        "Strophe eins Zeile A\nStrophe eins Zeile B\n\n"
        "Refrain Zeile 1\nRefrain Zeile 2\n\n"
        "Strophe zwei Zeile A\nStrophe zwei Zeile B"
    )
    aligned = align_lyrics(template, user_text)

    chorus = [s for s in aligned.sections if s.tag == "[Chorus]"]
    # Beide Chorus-Sektionen tragen denselben Text.
    assert chorus[0].lines == chorus[1].lines == ["Refrain Zeile 1", "Refrain Zeile 2"]

    prompt = aligned.to_suno_prompt()
    assert "[Verse]" in prompt and "[Chorus]" in prompt
    assert prompt.count("Refrain Zeile 1") == 2  # Chorus zweimal


def test_structured_input_preserved(blueprint_with_structure: SongBlueprint):
    template = build_template(blueprint_with_structure)
    user_text = "[Verse]\nmeine Strophe\n\n[Chorus]\nmein Refrain"
    aligned = align_lyrics(template, user_text)
    prompt = aligned.to_suno_prompt()
    assert "meine Strophe" in prompt
    assert "mein Refrain" in prompt


def test_clamp_prompt():
    text = "\n".join(f"Zeile {i}" for i in range(100))
    clamped = clamp_prompt(text, max_len=50)
    assert len(clamped) <= 50
