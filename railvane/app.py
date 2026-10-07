"""HTTP API and static UI."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import classify, history, library, packs, quality
from .areas import PHASES
from .config import load_workspace
from .frontmatter import schema_summary
from .index import Index
from .packs.installed import pack_entries

STATIC_DIR = Path(__file__).parent / "static"


def create_app(workspace_root: str | Path) -> FastAPI:
    root = Path(workspace_root).resolve()
    load_workspace(root)  # fail fast on a missing folder

    app = FastAPI(title="Railvane", version=__version__)
    app.state.index = Index(root, extra=pack_entries)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/workspace")
    def workspace():
        # Read on every request: the config is a file in git and can change any time
        return load_workspace(root).model_dump()

    @app.get("/api/schema")
    def schema():
        return {"frontmatter": schema_summary(), "phases": PHASES}

    for module in (library, classify, history, quality, packs):
        app.include_router(module.router)

    # The built UI is optional, so the API also runs during frontend development
    if (STATIC_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

    return app


def app_from_env() -> FastAPI:
    """Factory for `uvicorn --factory --reload` (development): reload needs an import path."""
    return create_app(os.environ.get("RAILVANE_WORKSPACE", "."))
