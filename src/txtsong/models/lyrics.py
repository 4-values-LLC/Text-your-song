"""Modelle für die Lyric-Aufbereitung (Template & ausgerichteter Text)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from txtsong.models.blueprint import SectionLabel


class LyricSection(BaseModel):
    """Eine Sektion der getaggten Lyric-Vorlage."""

    label: SectionLabel
    tag: str  # z. B. "[Verse]", "[Chorus]"
    target_lines: int  # Ziel-Zeilenzahl
    target_syllables: int | None = None  # falls aus Whisper bekannt
    vocal_cue: str | None = None  # z. B. "(whispered)"
    # Vom Nutzer eingefügter Text dieser Sektion (Zeilen).
    lines: list[str] = Field(default_factory=list)
    # Verweis auf eine frühere Sektion (Chorus-Wiederverwendung).
    repeat_of: int | None = None


class AlignedLyrics(BaseModel):
    """Der fertig auf die Songstruktur ausgerichtete Text."""

    sections: list[LyricSection] = Field(default_factory=list)

    def to_suno_prompt(self) -> str:
        """Rendert den Text im Suno-Format (Struktur-Tags + Vocal-Cues)."""
        blocks: list[str] = []
        for sec in self.sections:
            block: list[str] = []
            if sec.vocal_cue:
                block.append(sec.vocal_cue)
            block.append(sec.tag)
            block.extend(sec.lines)
            blocks.append("\n".join(block))
        return "\n\n".join(blocks).strip()
