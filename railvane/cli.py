"""Command line: `railvane serve <folder>` and `railvane lint <folder>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def _serve(args) -> int:
    import uvicorn

    from .app import create_app

    try:
        app = create_app(args.folder)
    except FileNotFoundError as e:
        print(f"railvane: {e}", file=sys.stderr)
        return 2
    print(f"Railvane {__version__} serving {args.folder} on http://{args.host}:{args.port}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def _lint(args) -> int:
    from .index import build
    from .lint import report, run_lint

    root = Path(args.folder).resolve()
    if not root.is_dir():
        print(f"railvane: workspace folder not found: {root}", file=sys.stderr)
        return 2
    snap = build(root)
    for err in snap.workspace.errors:
        print(f"railvane.yaml: {err}", file=sys.stderr)
    for src in snap.sources:
        if src.error:
            print(f"source {src.id}: {src.error}", file=sys.stderr)
    findings = run_lint(snap)
    paths = {}
    for e in snap.list():  # report paths relative to the folder, as editors and GitHub expect
        p = Path(e.abs_path) if e.abs_path else None
        paths[e.id] = p.relative_to(root).as_posix() if p and p.is_relative_to(root) else e.id
    if args.format == "json":
        print(report.as_json(findings))
    elif args.format == "github":
        print(report.github(findings, paths))
        print(report.text(findings, paths), file=sys.stderr)
    else:
        print(report.text(findings, paths))
    return 1 if report.fails(findings, args.fail_on) or snap.workspace.errors else 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # e.g. a cp1252 Windows console cannot print ⚠
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(prog="railvane", description="The guardrails manager for AI coding agents")
    parser.add_argument("--version", action="version", version=f"railvane {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="serve the Railvane UI for a workspace folder")
    serve.add_argument("folder", nargs="?", default=".", help="workspace folder (default: current folder)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8484)

    lint = sub.add_parser("lint", help="check guardrails; exit code 1 when findings reach --fail-on")
    lint.add_argument("folder", nargs="?", default=".")
    lint.add_argument("--format", choices=["text", "json", "github"], default="text")
    lint.add_argument("--fail-on", choices=["error", "warning", "info", "never"], default="error")

    args = parser.parse_args(argv)
    return _serve(args) if args.command == "serve" else _lint(args)


if __name__ == "__main__":
    raise SystemExit(main())
