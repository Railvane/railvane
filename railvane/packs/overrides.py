"""Local overrides of pack rules: your change lives in your workspace, the pack stays as is."""

from __future__ import annotations

from pathlib import Path

from ..edit import EditError
from ..textutil import sha
from ..wsgit import commit_workspace, write_text
from .installed import override_path


def save_override(snap, entry, text: str, base_hash: str, why: str) -> dict:
    if not why or not why.strip():
        raise EditError("say why you override this pack rule")
    if sha(entry.text) != base_hash:
        raise EditError("the file changed since you opened it; reload and try again")
    if text == entry.text:
        raise EditError("nothing changed")
    root = Path(snap.workspace.root)
    path = override_path(root, entry.pack["name"], entry.path)
    write_text(path, text)
    commit = commit_workspace(root, [path], f"Override {entry.path} from pack {entry.pack['name']}", why)
    return {"mode": "override", "commit": commit}


def drop_override(snap, entry, why: str | None) -> dict:
    root = Path(snap.workspace.root)
    path = override_path(root, entry.pack["name"], entry.path)
    if not path.exists():
        raise EditError("this rule has no local override")
    path.unlink()
    commit = commit_workspace(root, [path], f"Use upstream {entry.path} from pack {entry.pack['name']}", why)
    return {"commit": commit}
