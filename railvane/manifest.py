"""Sidecar manifest: metadata for files that have no frontmatter.

Lives in the workspace (the guardrails repo) at .railvane/manifest.yaml, keyed by
'<source-id>/<path>'. Source files are never rewritten to add metadata.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import RAILVANE_DIR

MANIFEST = f"{RAILVANE_DIR}/manifest.yaml"
FIELDS = ("type", "area", "visibility", "owner", "tags", "status", "scope", "promoted_to")


def manifest_path(ws_root: Path) -> Path:
    return Path(ws_root) / MANIFEST


def read_manifest(ws_root: Path) -> dict[str, dict]:
    file = manifest_path(ws_root)
    if not file.exists():
        return {}
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    files = data.get("files") or {}
    return {k: v for k, v in files.items() if isinstance(v, dict)}


def update_manifest(ws_root: Path, entries: dict[str, dict]) -> Path:
    """Merge entries (key -> metadata) into the manifest and write it back."""
    current = read_manifest(ws_root)
    for key, meta in entries.items():
        clean = {k: v for k, v in meta.items() if k in FIELDS and v not in (None, "", [])}
        current[key] = {**current.get(key, {}), **clean}
    file = manifest_path(ws_root)
    file.parent.mkdir(parents=True, exist_ok=True)
    body = {"version": 1, "files": dict(sorted(current.items()))}
    file.write_text("# Railvane sidecar manifest: metadata for files without frontmatter.\n"
                    + yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return file
