"""Richtet den vom Nutzer gelieferten Text auf die Songstruktur aus.

Zwei Eingabemodi:
- **strukturiert**: Der Text enthält bereits Struktur-Tags ([Verse], [Chorus] …)
  -> wird übernommen/validiert.
- **Freitext**: In Strophen (durch Leerzeilen getrennt) -> werden in Reihenfolge
  auf die Nicht-Wiederholungs-Sektionen gemappt; Chorus-Blöcke werden über die
  erkannten Wiederholungen automatisch dupliziert.
"""

from __future__ import annotations

import re

from txtsong.models.lyrics import AlignedLyrics, LyricSection

_TAG_RE = re.compile(r"^\s*[\[(]([^\])]+)[\])]\s*$")


def _looks_structured(text: str) -> bool:
    return bool(_TAG_RE.search(text) and any(_TAG_RE.match(l) for l in text.splitlines()))


def _parse_structured(text: str) -> list[list[str]]:
    """Zerlegt getaggten Text in Blöcke (Tag-Zeile wird verworfen)."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if _TAG_RE.match(line):
            current = []
            blocks.append(current)
        elif current is not None and line.strip():
            current.append(line.strip())
    return [b for b in blocks if b]


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


def align_lyrics(template: AlignedLyrics, user_text: str) -> AlignedLyrics:
    """Füllt die Template-Sektionen mit dem Nutzertext.

    Gibt eine neue ``AlignedLyrics``-Instanz zurück (Template bleibt unverändert).
    """
    blocks = (
        _parse_structured(user_text)
        if _looks_structured(user_text)
        else _parse_freeform(user_text)
    )

    # Sektionen, die eigenen Text brauchen (keine Instrumental-/Repeat-Sektionen).
    fillable = [
        s for s in template.sections if s.repeat_of is None and s.target_lines > 0
    ]

    filled: dict[int, list[str]] = {}
    for sec, block in zip(fillable, blocks):
        idx = template.sections.index(sec)
        filled[idx] = block

    out_sections: list[LyricSection] = []
    for i, sec in enumerate(template.sections):
        new = sec.model_copy(deep=True)
        if sec.repeat_of is not None:
            # Chorus-Wiederverwendung: Text der referenzierten Sektion übernehmen.
            new.lines = list(filled.get(sec.repeat_of, []))
        elif sec.target_lines > 0:
            new.lines = filled.get(i, [])
        out_sections.append(new)

    return AlignedLyrics(sections=out_sections)


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
