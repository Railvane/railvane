"""Install, remove, update and discover packs. Every change is a commit in the workspace."""

from __future__ import annotations

import difflib
from pathlib import Path

from ..config import PackRef, load_workspace, save_config
from ..gitutil import GitError, git
from ..history import why_of
from ..textutil import tokens
from ..wsgit import WriteError, commit_workspace, write_text
from .installed import load_ref, override_path
from .store import PackSource, open_pack, parse_version


class PackError(RuntimeError):
    pass


def _config(ws_root: Path):
    ws = load_workspace(ws_root)
    if ws.errors:
        raise PackError("railvane.yaml has errors; fix them first")
    return ws.config


def _save(ws_root: Path, config, subject: str, why: str | None) -> str | None:
    try:
        file = save_config(ws_root, config)
    except OSError as e:
        raise WriteError(f"cannot write railvane.yaml: {e}") from e
    return commit_workspace(ws_root, [file], subject, why)


def latest(ps: PackSource) -> tuple[str | None, str | None]:
    tags = ps.tags()
    return (tags[0][1], tags[0][2]) if tags else (None, None)


def install(ws_root: Path, source: str, path: str | None = None, version: str | None = None) -> dict:
    config = _config(ws_root)
    ps = open_pack(ws_root, source, path, fetch=True)
    version = version or latest(ps)[0]
    ref = ps.ref_for(version) if version else None
    meta = ps.meta(ref)
    if any(_name(ws_root, p) == meta.name for p in config.packs):
        raise PackError(f"pack {meta.name} is already installed")
    config.packs.append(PackRef(source=source, path=path, version=version, sha=ps.sha_of(ref)))
    commit = _save(ws_root, config, f"Install pack {meta.name} {version or '(unversioned)'}", None)
    return {"name": meta.name, "version": version, "commit": commit}


def _name(ws_root: Path, ref: PackRef) -> str | None:
    try:
        ps, at = load_ref(ws_root, ref)
        return ps.meta(at).name
    except (GitError, OSError, ValueError):
        return None


def _find(ws_root: Path, config, name: str) -> tuple[int, PackRef]:
    for i, ref in enumerate(config.packs):
        if _name(ws_root, ref) == name:
            return i, ref
    raise PackError(f"pack {name} is not installed")


def remove(ws_root: Path, name: str) -> dict:
    config = _config(ws_root)
    i, _ = _find(ws_root, config, name)
    config.packs.pop(i)
    return {"commit": _save(ws_root, config, f"Remove pack {name}", None)}


def _whys(ps: PackSource, old_ref: str, new_ref: str, rel: str) -> list[str]:
    path = f"{ps.subdir}/{rel}" if ps.subdir else rel
    out = git(["log", "--format=%b%x1e", f"{old_ref}..{new_ref}", "--", path], cwd=ps.repo, check=False)
    return [w for w in (why_of(b) for b in out.split("\x1e")) if w]


def check_update(ws_root: Path, ref: PackRef, fetch: bool = False) -> dict:
    ps = open_pack(ws_root, ref.source, ref.path, fetch=fetch)
    current_ref = ps.ref_for(ref.version) if ref.version else ref.sha
    meta = ps.meta(current_ref)
    new_version, new_ref = latest(ps)
    info = {"name": meta.name, "description": meta.description, "license": meta.license, "source": ref.source,
            "version": ref.version, "latest": new_version, "update": False, "major": False, "changes": []}
    old_files = ps.files(current_ref)
    info.update(rules=len(old_files), tokens=sum(tokens(t) for t in old_files.values()))
    cur, new = parse_version(ref.version or ""), parse_version(new_version or "")
    if not (cur and new and new > cur):
        return info
    new_files = ps.files(new_ref)
    info.update(update=True, major=new[0] > cur[0])
    for rel in sorted(set(old_files) | set(new_files)):
        old, neu = old_files.get(rel), new_files.get(rel)
        if old == neu:
            continue
        kind = "added" if old is None else "removed" if neu is None else "changed"
        diff = "".join(difflib.unified_diff((old or "").splitlines(True), (neu or "").splitlines(True),
                                            f"a/{rel}", f"b/{rel}"))
        info["changes"].append({"path": rel, "kind": kind, "diff": diff,
                                "why": _whys(ps, current_ref, new_ref, rel),
                                "overridden": override_path(ws_root, meta.name, rel).exists()})
    info["tokens_after"] = sum(tokens(t) for t in new_files.values())
    return info


def apply_update(ws_root: Path, name: str, keep: list[str], why: str | None) -> dict:
    """Move a pack to its latest version. Changed rules listed in `keep` stay as they are:
    their current text becomes a local override."""
    config = _config(ws_root)
    i, ref = _find(ws_root, config, name)
    ps = open_pack(ws_root, ref.source, ref.path)
    current_ref = ps.ref_for(ref.version) if ref.version else ref.sha
    new_version, new_ref = latest(ps)
    if not new_version or new_version == ref.version:
        raise PackError(f"{name} is already up to date")
    old_files, written = ps.files(current_ref), []
    for rel in keep:
        path = override_path(ws_root, name, rel)
        if rel in old_files and not path.exists():
            write_text(path, old_files[rel])
            written.append(path)
    config.packs[i] = PackRef(source=ref.source, path=ref.path, version=new_version, sha=ps.sha_of(new_ref))
    file = save_config(ws_root, config)
    subject = f"Update pack {name} to {new_version}" + (f" (kept {len(written)} rule(s))" if written else "")
    return {"version": new_version, "commit": commit_workspace(ws_root, [file, *written], subject, why)}


def discover(ws_root: Path, catalog: list[str], installed: set[str]) -> list[dict]:
    out = []
    for item in catalog:
        source, _, path = item.partition("#")
        try:
            ps = open_pack(ws_root, source, path or None)
            version, tag = latest(ps)
            meta, files = ps.meta(tag), ps.files(tag)
            out.append({"source": source, "path": path or None, "name": meta.name, "version": version,
                        "description": meta.description, "license": meta.license, "rules": len(files),
                        "tokens": sum(tokens(t) for t in files.values()), "installed": meta.name in installed})
        except (GitError, OSError, ValueError) as e:
            out.append({"source": item, "error": str(e)})
    return out
