"""Stufe D – Prompt-Builder: Blueprint + Text -> Suno-Style & -Lyrics."""

from txtsong.prompt.lyric_aligner import align_lyrics
from txtsong.prompt.lyrics_template import build_template
from txtsong.prompt.style_builder import build_style, derive_title, derive_vocal_gender

__all__ = [
    "build_style",
    "derive_title",
    "derive_vocal_gender",
    "build_template",
    "align_lyrics",
]
