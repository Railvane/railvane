"""Command line entry point: `railvane serve <folder>`."""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="railvane", description="The guardrails manager for AI coding agents")
    parser.add_argument("--version", action="version", version=f"railvane {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="serve the Railvane UI for a workspace folder")
    serve.add_argument("folder", nargs="?", default=".", help="workspace folder (default: current folder)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8484)

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        from .app import create_app

        try:
            app = create_app(args.folder)
        except FileNotFoundError as e:
            print(f"railvane: {e}", file=sys.stderr)
            return 2
        print(f"Railvane {__version__} serving {args.folder} on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
