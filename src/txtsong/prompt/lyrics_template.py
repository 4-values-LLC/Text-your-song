"""Erzeugt aus der Songstruktur eine getaggte Lyric-Vorlage.

Die Vorlage gibt dem Nutzer pro Sektion das passende Struktur-Tag, die
Ziel-Zeilenzahl (und – falls Whisper lief – ein Silbenbudget) vor. Wiederholte
Chorus-Sektionen werden erkannt und referenzieren denselben Block.
"""

from __future__ import annotations

from txtsong.models.blueprint import SectionLabel, SongBlueprint
from txtsong.models.lyrics import AlignedLyrics, LyricSection

# Anzeigename der Struktur-Tags (Suno-Konvention, englisch).
_TAG = {
    SectionLabel.INTRO: "[Intro]",
    SectionLabel.VERSE: "[Verse]",
    SectionLabel.PRECHORUS: "[Pre-Chorus]",
    SectionLabel.CHORUS: "[Chorus]",
    SectionLabel.BRIDGE: "[Bridge]",
    SectionLabel.DROP: "[Drop]",
    SectionLabel.BREAKDOWN: "[Breakdown]",
    SectionLabel.OUTRO: "[Outro]",
    SectionLabel.INSTRUMENTAL: "[Instrumental]",
}

# Default-Zeilenzahl je Sektionstyp (falls keine Whisper-Daten vorliegen).
_DEFAULT_LINES = {
    SectionLabel.INTRO: 0,
    SectionLabel.VERSE: 4,
    SectionLabel.PRECHORUS: 2,
    SectionLabel.CHORUS: 3,
    SectionLabel.BRIDGE: 2,
    SectionLabel.DROP: 0,
    SectionLabel.BREAKDOWN: 0,
    SectionLabel.OUTRO: 1,
    SectionLabel.INSTRUMENTAL: 0,
}


def build_template(bp: SongBlueprint) -> AlignedLyrics:
    """Baut die leere Lyric-Vorlage aus der erkannten Struktur."""
    sections: list[LyricSection] = []
    first_chorus_idx: int | None = None

    for i, sec in enumerate(bp.structure.sections):
        target = sec.lyric_lines if sec.lyric_lines is not None else _DEFAULT_LINES.get(
            sec.label, 2
        )
        repeat_of = None
        # Wiederholte Chorus-Sektionen auf den ersten Chorus zeigen lassen.
        if sec.label == SectionLabel.CHORUS:
            if first_chorus_idx is None:
                first_chorus_idx = i
            else:
                repeat_of = first_chorus_idx

        sections.append(
            LyricSection(
                label=sec.label,
                tag=_TAG.get(sec.label, f"[{sec.label.value}]"),
                target_lines=max(0, target),
                repeat_of=repeat_of,
            )
        )

    return AlignedLyrics(sections=sections)


def template_as_text(template: AlignedLyrics) -> str:
    """Rendert die Vorlage als ausfüllbaren Text (mit Hinweisen je Sektion)."""
    blocks: list[str] = []
    for i, sec in enumerate(template.sections):
        if sec.repeat_of is not None:
            blocks.append(f"{sec.tag}\n(→ wiederholt Chorus aus Sektion {sec.repeat_of})")
            continue
        if sec.target_lines == 0:
            blocks.append(f"{sec.tag}\n(instrumental – kein Text)")
            continue
        hint = f"({sec.target_lines} Zeilen)"
        placeholder = "\n".join(["..."] * sec.target_lines)
        blocks.append(f"{sec.tag} {hint}\n{placeholder}")
    return "\n\n".join(blocks)
