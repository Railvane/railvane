"""Copies: a master guardrail lives once in the workspace; source repositories get a copy that
agents read (CLAUDE.md imports it). Railvane shows whether each copy is in sync and syncs them."""

from __future__ import annotations

from pathlib import Path

from .config import Copy


def same_text(a: str, b: str) -> bool:
    return a.replace("\r\n", "\n").strip() == b.replace("\r\n", "\n").strip()


def entry_id_for(sources, path: Path) -> str | None:
    """Id of the guardrail at an absolute path, via the source that contains it."""
    path = path.resolve()
    for src in sources:
        if src.root and path.is_relative_to(src.root):
            return f"{src.id}/{path.relative_to(src.root).as_posix()}"
    return None


def link_copies(entries: dict, sources, ws) -> None:
    root = Path(ws.root)
    for c in ws.config.copies:
        master_id = entry_id_for(sources, root / c.master)
        master = entries.get(master_id) if master_id else None
        copy_id = f"{c.source}/{c.path}"
        copy = entries.get(copy_id)
        status = "missing" if not copy else "in_sync" if master and same_text(master.text, copy.text) else "drift"
        if master:
            master.copies.append({"id": copy_id, "source": c.source, "path": c.path, "status": status})
        if copy:
            copy.copy_of, copy.copy_status = master_id or c.master, status
            if master:  # a copy carries the metadata of its master
                for attr in ("type", "area", "phase", "visibility", "owner", "tags", "status", "scope"):
                    setattr(copy, attr, getattr(master, attr))
                copy.confirmed, copy.meta_source, copy.confidence = True, "master", 1.0


def rows(snap) -> list[dict]:
    """All copies with their state, for the Repositories view."""
    out = []
    for c in snap.workspace.config.copies:
        copy = snap.entries.get(f"{c.source}/{c.path}")
        out.append({"master": c.master, "source": c.source, "path": c.path,
                    "status": copy.copy_status if copy else "missing",
                    "readonly": next((s.readonly for s in snap.sources if s.id == c.source), None)})
    return out


def plan_sync(snap, source_id: str | None = None) -> dict[str, dict[Path, str]]:
    """Files to write per source id: copy path -> master text, for every copy not in sync."""
    root = Path(snap.workspace.root)
    todo: dict[str, dict[Path, str]] = {}
    for c in snap.workspace.config.copies:
        if source_id and c.source != source_id:
            continue
        src = next((s for s in snap.sources if s.id == c.source), None)
        master_file = root / c.master
        if not src or not src.root or not master_file.exists():
            continue
        master = master_file.read_text(encoding="utf-8", errors="replace")
        target = src.root / c.path
        current = target.read_text(encoding="utf-8", errors="replace") if target.exists() else None
        if current is None or not same_text(master, current):
            todo.setdefault(c.source, {})[target] = master
    return todo


def register(config, new: list[Copy]) -> list[Copy]:
    """Add copies to the config (skipping ones it already has); returns what was added."""
    known = {(c.source, c.path) for c in config.copies}
    added = [c for c in new if (c.source, c.path) not in known]
    config.copies.extend(added)
    return added
