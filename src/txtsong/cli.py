"""Kommandozeilen-Interface (für Tests/Entwicklung ohne Web-UI).

Verwendung:
    python -m txtsong.cli analyze <url|datei>
    python -m txtsong.cli template <job_id>
    python -m txtsong.cli remix <job_id> --lyrics text.txt [--dry-run]
    python -m txtsong.cli run <url|datei> --lyrics text.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from txtsong.pipeline import build_request, run_analysis, run_remix
from txtsong.utils.workspace import get_workspace


def _read_lyrics(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_analyze(args: argparse.Namespace) -> int:
    result = run_analysis(args.source, job_id=args.job_id)
    print(f"\nJob-ID: {result.job_id}")
    print("\n" + result.report_md)
    print("\n--- Lyric-Vorlage (eigenen Text einfügen) ---\n")
    print(result.template_text)
    return 0


def cmd_template(args: argparse.Namespace) -> int:
    from txtsong.models.blueprint import SongBlueprint
    from txtsong.prompt.lyrics_template import build_template, template_as_text

    ws = get_workspace(args.job_id, create=False)
    bp = SongBlueprint.from_json(ws.blueprint_path.read_text(encoding="utf-8"))
    print(template_as_text(build_template(bp)))
    return 0


def cmd_remix(args: argparse.Namespace) -> int:
    lyrics = _read_lyrics(args.lyrics) if args.lyrics else ""
    out = run_remix(args.job_id, lyrics, instrumental=args.instrumental, dry_run=args.dry_run)
    if args.dry_run:
        print("--- Dry-Run: vorbereiteter Suno-Request ---\n")
        print(out.model_dump_json(indent=2))  # type: ignore[union-attr]
    else:
        print("Remix fertig:")
        for t in out.tracks:  # type: ignore[union-attr]
            print(f"  - {t.local_path or t.audio_url}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    analysis = run_analysis(args.source, job_id=args.job_id)
    lyrics = _read_lyrics(args.lyrics) if args.lyrics else ""
    out = run_remix(
        analysis.job_id, lyrics, instrumental=args.instrumental, dry_run=args.dry_run
    )
    print(f"Job-ID: {analysis.job_id}")
    if not args.dry_run:
        for t in out.tracks:  # type: ignore[union-attr]
            print(f"  - {t.local_path or t.audio_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="txtsong", description="Song-Analyse & Suno-Remix")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="Song analysieren -> Blueprint + Report + Template")
    a.add_argument("source", help="YouTube-/Spotify-URL oder Pfad zur Audiodatei")
    a.add_argument("--job-id", default=None)
    a.set_defaults(func=cmd_analyze)

    t = sub.add_parser("template", help="Lyric-Vorlage für einen Job ausgeben")
    t.add_argument("job_id")
    t.set_defaults(func=cmd_template)

    r = sub.add_parser("remix", help="Remix für einen analysierten Job erzeugen")
    r.add_argument("job_id")
    r.add_argument("--lyrics", help="Pfad zur Textdatei mit eigenem Text (entfällt bei --instrumental)")
    r.add_argument("--instrumental", action="store_true", help="Vocal-losen Remix erzeugen (Text ignoriert)")
    r.add_argument("--dry-run", action="store_true", help="Nur Request bauen, nicht senden")
    r.set_defaults(func=cmd_remix)

    run = sub.add_parser("run", help="Komplett: analysieren + remixen")
    run.add_argument("source")
    run.add_argument("--lyrics", help="Pfad zur Textdatei mit eigenem Text (entfällt bei --instrumental)")
    run.add_argument("--instrumental", action="store_true", help="Vocal-losen Remix erzeugen (Text ignoriert)")
    run.add_argument("--job-id", default=None)
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)

    return p


def app(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(app())
