"""Resolve configured sources to folders on disk and find guardrail files in them.

Git sources are cloned into a disposable cache (RAILVANE_CACHE, default
~/.cache/railvane). Deleting the cache loses nothing.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import globs
from .config import Source, WorkspaceConfig
from .gitutil import GitError, display_path, git, repo_info

FETCH_INTERVAL = 60  # seconds between automatic fetches of a git source
ALWAYS_PRUNE = {".git", "node_modules", ".venv", "__pycache__", ".railvane"}
_last_fetch: dict[str, float] = {}


@dataclass
class ResolvedSource:
    id: str
    kind: str                  # "path" | "git"
    location: str              # path or URL as configured
    root: Path | None
    readonly: bool
    include: list[str]
    exclude: list[str]
    branch: str | None = None
    error: str | None = None
    files: list[str] = field(default_factory=list)  # posix paths relative to root
    repo: dict | None = None   # see gitutil.repo_info

    def summary(self) -> dict:
        return {"id": self.id, "kind": self.kind, "location": self.location, "branch": self.branch,
                "readonly": self.readonly, "error": self.error, "files": len(self.files),
                "root": str(self.root) if self.root else None, "display_root": display_path(self.root),
                "repo": self.repo}


def cache_dir() -> Path:
    return Path(os.environ.get("RAILVANE_CACHE") or Path.home() / ".cache" / "railvane")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-") or "source"


def clone_or_update(url: str, branch: str | None = None, force: bool = False) -> Path:
    """Clone url into the cache, or fetch + fast-forward an existing clone."""
    name = _slug(url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1])
    target = cache_dir() / "git" / f"{hashlib.sha1(url.encode()).hexdigest()[:10]}-{name}"
    if not (target / ".git").exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "-q", *(["--branch", branch] if branch else []), url, str(target)]
        git(args, network=True, timeout=300)
        _last_fetch[url] = time.time()
        return target
    if force or time.time() - _last_fetch.get(url, 0) > FETCH_INTERVAL:
        git(["fetch", "-q", "--tags", "origin"], cwd=target, network=True)
        upstream = f"origin/{branch}" if branch else "@{upstream}"
        git(["merge", "-q", "--ff-only", upstream], cwd=target, check=False)
        _last_fetch[url] = time.time()
    return target


def scan_folder(root: Path, include: list[str], exclude: list[str]) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_PRUNE
                       and not globs.dir_excluded(f"{rel_dir}/{d}".lstrip("/"), exclude)]
        for f in filenames:
            rel = f"{rel_dir}/{f}".lstrip("/")
            if globs.match_any(rel, include) and not globs.match_any(rel, exclude):
                found.append(rel)
    return sorted(found)


def resolve_sources(ws_root: Path, config: WorkspaceConfig, fetch: bool = False) -> list[ResolvedSource]:
    out: list[ResolvedSource] = []
    used: set[str] = set()
    for src in config.sources:
        out.append(_resolve(ws_root, config, src, used, fetch))
    return out


def _resolve(ws_root: Path, config: WorkspaceConfig, src: Source, used: set[str], fetch: bool) -> ResolvedSource:
    include = src.include or config.include
    exclude = (src.exclude or []) + config.exclude
    if src.git:
        base = src.name or src.git.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    else:
        p = (ws_root / src.path).resolve()
        base = src.name or (config.name if p == ws_root else p.name)
    sid = _slug(base)
    n = 2
    while sid in used:
        sid, n = f"{_slug(base)}-{n}", n + 1
    used.add(sid)
    rs = ResolvedSource(id=sid, kind="git" if src.git else "path", location=src.git or src.path,
                        root=None, readonly=src.readonly, include=include, exclude=exclude, branch=src.branch)
    try:
        rs.root = clone_or_update(src.git, src.branch, force=fetch) if src.git else (ws_root / src.path).resolve()
        if not rs.root.is_dir():
            raise FileNotFoundError(f"folder not found: {rs.root}")
        rs.files = scan_folder(rs.root, include, exclude)
        rs.repo = repo_info(rs.root)
    except (GitError, OSError) as e:
        rs.error = str(e)
    return rs
