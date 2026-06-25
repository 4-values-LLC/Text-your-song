"""Erzeugt aus dem Blueprint den englischen Suno-Style-String.

Folgt der bewährten Suno-Formel:
    Genre + Tempo(BPM) + Mood + Instrumente + Vocal-Style + Ära
(4–7 Deskriptoren liefern die besten Ergebnisse.)
"""

from __future__ import annotations

from txtsong.models.blueprint import SongBlueprint

# Stimmungs-Begriffe sind bereits englisch (siehe analysis._infer_mood),
# diese Map fängt evtl. deutsche Werte ab.
_MOOD_EN = {
    "energetic": "energetic",
    "laid-back": "laid-back",
    "uplifting": "uplifting",
    "melancholic": "melancholic",
    "bright": "bright",
    "moody": "moody",
}

_SCALE_EN = {"major": "major", "minor": "minor"}


def build_style(bp: SongBlueprint, *, max_len: int = 1000, instrumental: bool = False) -> str:
    """Baut den Style-String (englisch), begrenzt auf ``max_len`` Zeichen.

    ``instrumental`` beschreibt die **gewünschte Ausgabe**, nicht die Quelle:
    bei ``True`` wird „instrumental" angehängt und kein Vocal-Style ergänzt; bei
    ``False`` wird **immer** ein Vocal-Style ergänzt — auch wenn der Quell-Track
    instrumental war (der Nutzer legt ja seinen eigenen Text darüber).
    """
    parts: list[str] = []

    # Genre / Subgenre
    if bp.production.genre:
        genre = bp.production.genre
        if bp.production.subgenre and bp.production.subgenre not in genre:
            genre = f"{bp.production.subgenre} {genre}"
        parts.append(genre)

    # Tempo (Suno reagiert stark auf konkrete BPM-Zahlen)
    if bp.tempo.bpm:
        parts.append(f"{bp.tempo.bpm:.0f} BPM")

    # Tonart
    if bp.tonality.key and bp.tonality.scale:
        parts.append(f"{bp.tonality.key} {_SCALE_EN.get(bp.tonality.scale, bp.tonality.scale)}")

    # Mood
    for m in bp.production.mood:
        parts.append(_MOOD_EN.get(m, m))

    # Instrumente
    parts.extend(bp.instrumentation.instruments)

    # Vocal-Style — richtet sich nach der GEWÜNSCHTEN Ausgabe, nicht der Quelle.
    if instrumental:
        parts.append("instrumental")
    else:
        gender = {"m": "male", "f": "female"}.get(bp.vocals.gender_guess or "", "")
        vstyle = bp.vocals.style or "lead vocals"
        parts.append(f"{gender} {vstyle}".strip())

    # Klangbild / Ära
    if bp.spectral.brightness:
        parts.append(f"{bp.spectral.brightness} mix")
    if bp.production.era:
        parts.append(f"{bp.production.era} production")

    # Deduplizieren (Reihenfolge bewahren), leere Teile entfernen.
    seen: set[str] = set()
    clean: list[str] = []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            clean.append(p)

    style = ", ".join(clean)
    return style[:max_len].rstrip(", ")


def derive_title(bp: SongBlueprint, *, max_len: int = 100) -> str:
    """Leitet einen Titel ab (Original-Titel als Basis, sonst Genre-basiert)."""
    base = bp.source.title or f"{bp.production.genre or 'Song'} Remix"
    title = f"{base} (Remix)" if "remix" not in base.lower() else base
    return title[:max_len]


def derive_vocal_gender(bp: SongBlueprint) -> str | None:
    """Liefert das Vocal-Geschlecht für die Suno-Anfrage ('m'/'f')."""
    if bp.vocals.present and bp.vocals.gender_guess in ("m", "f"):
        return bp.vocals.gender_guess
    return None


def derive_negative_tags(bp: SongBlueprint) -> str | None:
    """Schlägt negativeTags vor, um den Stil sauber zu halten."""
    tags: list[str] = []
    if bp.vocals.present is False:
        tags.append("vocals")
    return ", ".join(tags) if tags else None
