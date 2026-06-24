"""Rendert einen SongBlueprint als deutschsprachigen Producer-Report (Markdown)."""

from __future__ import annotations

from txtsong.models.blueprint import SongBlueprint


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def render_report(bp: SongBlueprint) -> str:
    """Erzeugt den Markdown-Report aus dem Blueprint."""
    s = bp.source
    lines: list[str] = []

    title = s.title or "Unbekannter Titel"
    artist = f" – {s.artist}" if s.artist else ""
    lines.append(f"# Producer-Analyse: {title}{artist}\n")

    # --- Überblick ---
    lines.append("## Überblick\n")
    if s.duration_s:
        lines.append(f"- **Länge:** {_fmt_time(s.duration_s)} ({s.duration_s:.0f}s)")
    lines.append(f"- **Quelle:** {s.origin}" + (f" ({s.url})" if s.url else ""))
    if bp.production.genre:
        sub = f" / {bp.production.subgenre}" if bp.production.subgenre else ""
        lines.append(f"- **Genre:** {bp.production.genre}{sub}")
    if bp.production.mood:
        lines.append(f"- **Stimmung:** {', '.join(bp.production.mood)}")
    if bp.production.era:
        lines.append(f"- **Ära/Produktion:** {bp.production.era}")
    lines.append("")

    # --- Rhythmus & Tonart ---
    lines.append("## Rhythmus & Harmonie\n")
    t = bp.tempo
    if t.bpm:
        conf = f" (Konfidenz {t.bpm_confidence:.0%})" if t.bpm_confidence else ""
        lines.append(f"- **Tempo:** {t.bpm:.0f} BPM{conf}, {t.tempo_stability or '–'}")
    if t.time_signature:
        lines.append(f"- **Taktart:** {t.time_signature}")
    ton = bp.tonality
    if ton.key:
        scale_de = {"major": "Dur", "minor": "Moll"}.get(ton.scale or "", ton.scale or "")
        kconf = f" (Konfidenz {ton.key_confidence:.0%})" if ton.key_confidence else ""
        lines.append(f"- **Tonart:** {ton.key} {scale_de}{kconf}")
    lines.append("")

    # --- Struktur ---
    lines.append("## Songstruktur\n")
    if bp.structure.form_summary:
        lines.append(f"**Form:** `{bp.structure.form_summary}`\n")
    if bp.structure.sections:
        lines.append("| # | Sektion | Start | Ende | Takte | Energie | Zeilen |")
        lines.append("|---|---------|-------|------|-------|---------|--------|")
        for sec in bp.structure.sections:
            bars = str(sec.bars) if sec.bars is not None else "–"
            energy = f"{sec.energy:.2f}" if sec.energy is not None else "–"
            ll = str(sec.lyric_lines) if sec.lyric_lines is not None else "–"
            lines.append(
                f"| {sec.index} | {sec.label.value} | {_fmt_time(sec.start_s)} | "
                f"{_fmt_time(sec.end_s)} | {bars} | {energy} | {ll} |"
            )
    lines.append("")

    # --- Instrumentierung ---
    instr = bp.instrumentation
    if instr.stems_detected or instr.instruments:
        lines.append("## Instrumentierung\n")
        if instr.stems_detected:
            lines.append(f"- **Stems erkannt:** {', '.join(instr.stems_detected)}")
        if instr.instruments:
            lines.append(f"- **Instrumente (abgeleitet):** {', '.join(instr.instruments)}")
        if instr.drum_density:
            lines.append(f"- **Drum-Dichte:** {instr.drum_density}")
        if instr.bass_prominence:
            lines.append(f"- **Bass-Präsenz:** {instr.bass_prominence}")
        lines.append("")

    # --- Vocals ---
    v = bp.vocals
    if v.present is not None:
        lines.append("## Vocals\n")
        if v.present:
            gender = {"m": "männlich", "f": "weiblich"}.get(v.gender_guess or "", "unbekannt")
            lines.append(f"- **Gesang:** vorhanden ({gender})")
            if v.style:
                lines.append(f"- **Stil:** {v.style}")
            if v.language:
                lines.append(f"- **Sprache:** {v.language}")
            if v.lyrics_transcribed:
                lines.append("\n**Transkribierter Originaltext (Referenz):**\n")
                lines.append("```\n" + v.lyrics_transcribed.strip() + "\n```")
        else:
            lines.append("- **Gesang:** instrumental / nicht erkannt")
        lines.append("")

    # --- Mix / Dynamik ---
    d = bp.dynamics
    sp = bp.spectral
    lines.append("## Mix & Klangbild\n")
    if d.loudness_lufs_est is not None:
        lines.append(f"- **Lautheit (geschätzt):** {d.loudness_lufs_est} LUFS")
    if d.dynamic_range:
        dr_de = {"compressed": "komprimiert", "moderate": "moderat", "wide": "weit"}
        lines.append(f"- **Dynamikumfang:** {dr_de.get(d.dynamic_range, d.dynamic_range)}")
    if sp.brightness:
        br_de = {"dark": "dunkel", "balanced": "ausgewogen", "bright": "hell"}
        lines.append(f"- **Klangfarbe:** {br_de.get(sp.brightness, sp.brightness)}")
    if sp.centroid_hz_mean:
        lines.append(f"- **Spektral-Schwerpunkt:** {sp.centroid_hz_mean:.0f} Hz")
    lines.append("")

    if bp.production.production_notes:
        lines.append("## Produktions-Notizen\n")
        lines.append(bp.production.production_notes)
        lines.append("")

    return "\n".join(lines).strip() + "\n"
