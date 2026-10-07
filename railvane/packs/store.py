"""Read packs from git (at a tag) or from a working folder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from pydantic import BaseModel, ConfigDict

from ..gitutil import GitError, git, repo_root
from ..sources import clone_or_update

PACK_FILE = "railvane-pack.yaml"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class PackMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    version: str = "0.0.0"
    description: str = ""
    license: str | None = None
    owner: str | None = None


def parse_version(v: str) -> tuple[int, int, int] | None:
    m = SEMVER.match(v.lstrip("v"))
    return tuple(int(x) for x in m.groups()) if m else None


def bump(v: str, level: str) -> str:
    major, minor, patch = parse_version(v) or (0, 0, 0)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "__", name)


@dataclass
class PackSource:
    """Where a pack lives: a repository (or plain folder) plus an optional sub folder."""
    source: str
    folder: Path              # the pack folder on disk (working tree)
    repo: Path | None         # git repository containing it, if any
    subdir: str               # pack folder relative to repo ('' = repo root)

    @property
    def tag_prefix(self) -> str:
        return f"{self.subdir}/v" if self.subdir else "v"

    def tags(self) -> list[tuple[tuple[int, int, int], str, str]]:
        """(version tuple, version string, tag name), newest first."""
        if not self.repo:
            return []
        out = []
        for tag in git(["tag", "-l", f"{self.tag_prefix}*"], cwd=self.repo).split():
            v = tag[len(self.tag_prefix):]
            if parsed := parse_version(v):
                out.append((parsed, v, tag))
        return sorted(out, reverse=True)

    def ref_for(self, version: str | None) -> str | None:
        if not version or not self.repo:
            return None
        for _, v, tag in self.tags():
            if v == version:
                return tag
        raise GitError(f"version {version} not found (no tag {self.tag_prefix}{version})")

    def sha_of(self, ref: str | None) -> str | None:
        if not self.repo:
            return None
        return git(["rev-list", "-n1", ref or "HEAD"], cwd=self.repo).strip()

    def files(self, ref: str | None) -> dict[str, str]:
        """Markdown files of the pack (relative to the pack folder) at ref, or the working tree."""
        out = {}
        if ref and self.repo:
            names = git(["ls-tree", "-r", "--name-only", ref, "--", self.subdir or "."], cwd=self.repo).split("\n")
            for name in filter(None, names):
                rel = name[len(self.subdir) + 1:] if self.subdir else name
                if _is_rule(rel):
                    out[rel] = git(["show", f"{ref}:{name}"], cwd=self.repo)
        else:
            for f in sorted(self.folder.rglob("*.md*")):
                rel = f.relative_to(self.folder).as_posix()
                if _is_rule(rel) and ".git/" not in rel:
                    out[rel] = f.read_text(encoding="utf-8", errors="replace")
        return out

    def meta(self, ref: str | None) -> PackMeta:
        if ref and self.repo:
            path = f"{self.subdir}/{PACK_FILE}" if self.subdir else PACK_FILE
            text = git(["show", f"{ref}:{path}"], cwd=self.repo)
        else:
            text = (self.folder / PACK_FILE).read_text(encoding="utf-8")
        return PackMeta.model_validate(yaml.safe_load(text) or {})


def _is_rule(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.suffix in (".md", ".mdc") and p.name.lower() not in ("readme.md", "changelog.md", "license.md")


def open_pack(ws_root: Path, source: str, path: str | None = None, fetch: bool = False) -> PackSource:
    """source: git URL, or a folder relative to the workspace. path: sub folder in the source."""
    if "://" in source or source.startswith("git@"):
        base = clone_or_update(source, force=fetch)
    else:
        base = (ws_root / source).resolve()
    folder = (base / path).resolve() if path else base
    repo =repo_root(folder) if folder.exists() else None
    subdir = folder.relative_to(repo).as_posix() if repo else ""
    return PackSource(source=source, folder=folder, repo=repo, subdir="" if subdir == "." else subdir)
