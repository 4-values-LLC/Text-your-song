"""Richtet den vom Nutzer gelieferten Text auf die Songstruktur aus.

Zwei Eingabemodi:
- **strukturiert**: Der Text enthält bereits Struktur-Tags ([Verse], [Chorus] …)
  -> die Struktur des Nutzers wird übernommen (Tags normalisiert, leere
  Chorus-Wiederholungen mit dem ersten Chorus gefüllt).
- **Freitext**: In Strophen (durch Leerzeilen getrennt) -> werden in Reihenfolge
  auf die Nicht-Wiederholungs-Sektionen der Vorlage gemappt; Chorus-Blöcke werden
  über die erkannten Wiederholungen automatisch dupliziert.
"""

from __future__ import annotations

import re

from txtsong.models.blueprint import SectionLabel
from txtsong.models.lyrics import AlignedLyrics, LyricSection

_TAG_RE = re.compile(r"^\s*[\[(]\s*([^\])]+?)\s*[\])]\s*$")

# Tag-Name (klein) -> Sektions-Label.
_LABEL_ALIASES = {
    "intro": SectionLabel.INTRO,
    "verse": SectionLabel.VERSE,
    "pre-chorus": SectionLabel.PRECHORUS,
    "prechorus": SectionLabel.PRECHORUS,
    "pre chorus": SectionLabel.PRECHORUS,
    "chorus": SectionLabel.CHORUS,
    "hook": SectionLabel.CHORUS,
    "refrain": SectionLabel.CHORUS,
    "bridge": SectionLabel.BRIDGE,
    "drop": SectionLabel.DROP,
    "breakdown": SectionLabel.BREAKDOWN,
    "outro": SectionLabel.OUTRO,
    "instrumental": SectionLabel.INSTRUMENTAL,
}

# Kanonische (englische) Tag-Schreibweise je Label (Suno-Konvention).
_CANON_TAG = {
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


def _label_from_tag(name: str) -> SectionLabel | None:
    return _LABEL_ALIASES.get(name.strip().lower())


def _looks_structured(text: str) -> bool:
    """True, wenn mindestens eine Zeile ein Struktur-Tag ist."""
    return any(_TAG_RE.match(line) for line in text.splitlines())


def _parse_tagged(text: str) -> list[tuple[str, list[str]]]:
    """Zerlegt getaggten Text in (Tag-Name, Zeilen)-Blöcke.

    Zeilen vor dem ersten Tag werden ignoriert.
    """
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        m = _TAG_RE.match(line)
        if m:
            current = []
            blocks.append((m.group(1), current))
        elif current is not None and line.strip():
            current.append(line.strip())
    return blocks


def _parse_freeform(text: str) -> list[list[str]]:
    """Zerlegt Freitext in Strophen (durch Leerzeilen getrennt)."""
    stanzas: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.strip())
        elif current:
            stanzas.append(current)
            current = []
    if current:
        stanzas.append(current)
    return stanzas


def _align_structured(user_text: str) -> AlignedLyrics:
    """Übernimmt die vom Nutzer vorgegebene Tag-Struktur (normalisiert)."""
    out: list[LyricSection] = []
    first_chorus_lines: list[str] | None = None
    for raw_tag, lines in _parse_tagged(user_text):
        label = _label_from_tag(raw_tag)
        tag = _CANON_TAG.get(label, f"[{raw_tag.strip().title()}]") if label else f"[{raw_tag.strip()}]"

        if label == SectionLabel.CHORUS:
            if first_chorus_lines is None:
                first_chorus_lines = lines
            elif not lines:
                # Leerer Folge-Chorus -> ersten Chorus wiederverwenden.
                lines = list(first_chorus_lines)

        out.append(
            LyricSection(
                label=label or SectionLabel.VERSE,
                tag=tag,
                target_lines=len(lines),
                lines=lines,
            )
        )
    return AlignedLyrics(sections=out)


def _align_freeform(template: AlignedLyrics, user_text: str) -> AlignedLyrics:
    """Mappt Freitext-Strophen in Reihenfolge auf die Vorlagen-Sektionen."""
    blocks = _parse_freeform(user_text)

    fillable = [
        s for s in template.sections if s.repeat_of is None and s.target_lines > 0
    ]
    filled: dict[int, list[str]] = {}
    for sec, block in zip(fillable, blocks):
        filled[template.sections.index(sec)] = block

    out_sections: list[LyricSection] = []
    for i, sec in enumerate(template.sections):
        new = sec.model_copy(deep=True)
        if sec.repeat_of is not None:
            new.lines = list(filled.get(sec.repeat_of, []))
        elif sec.target_lines > 0:
            new.lines = filled.get(i, [])
        out_sections.append(new)
    return AlignedLyrics(sections=out_sections)


def align_lyrics(template: AlignedLyrics, user_text: str) -> AlignedLyrics:
    """Füllt/erzeugt die Lyric-Sektionen aus dem Nutzertext.

    Strukturierter Text (mit Tags) bestimmt die Struktur selbst; Freitext wird auf
    die erkannte Vorlage gemappt. Das Template bleibt unverändert.
    """
    if _looks_structured(user_text):
        return _align_structured(user_text)
    return _align_freeform(template, user_text)


def clamp_prompt(prompt: str, *, max_len: int) -> str:
    """Kürzt den Lyric-Prompt auf das Suno-Limit (an Zeilengrenzen)."""
    if len(prompt) <= max_len:
        return prompt
    lines = prompt.splitlines()
    out: list[str] = []
    total = 0
    for line in lines:
        if total + len(line) + 1 > max_len:
            break
        out.append(line)
        total += len(line) + 1
    return "\n".join(out)
