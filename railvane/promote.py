"""Promote a memory to a rule: the agent's note becomes a real guardrail in the workspace —
shareable, checked and versioned. The memory is marked as promoted (in the sidecar)."""

from __future__ import annotations

from pathlib import Path

from .areas import AREA_PHASE
from .copies import entry_id_for
from .manifest import manifest_path, update_manifest
from .repowrite import RepoWriteError
from .wsgit import commit_workspace, write_text


def promote(snap, entry, target: str, text: str, area: str, visibility: str, why: str | None) -> dict:
    if entry.type != "memory":
        raise RepoWriteError("only memory files can be promoted")
    if area not in AREA_PHASE:
        raise RepoWriteError(f"unknown area '{area}'")
    if visibility not in ("private", "shared"):
        raise RepoWriteError("visibility must be private or shared")
    ws_root = Path(snap.workspace.root)
    path = (ws_root / target).resolve()
    if not path.is_relative_to(ws_root) or path.suffix != ".md":
        raise RepoWriteError("the new rule must be a .md file inside the workspace")
    if path.exists():
        raise RepoWriteError(f"{target} already exists")
    if not text.strip():
        raise RepoWriteError("the rule is empty")
    write_text(path, text if text.endswith("\n") else text + "\n")
    new_id = entry_id_for(snap.sources, path)
    meta = {entry.id: {"promoted_to": new_id or target, "status": "deprecated"}}
    if new_id:
        owner = entry.owner or snap.workspace.config.defaults.owner or "@unassigned"
        meta[new_id] = {"type": "project-rules", "area": area, "visibility": visibility, "owner": owner}
    update_manifest(ws_root, meta)
    sha = commit_workspace(ws_root, [path, manifest_path(ws_root)], f"Promote {entry.title} to a rule", why)
    return {"id": new_id, "path": target, "commit": sha,
            "note": None if new_id else "saved, but no source includes this path — add it to a source's include"}
