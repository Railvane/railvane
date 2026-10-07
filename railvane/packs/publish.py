"""Publish packs you author: share check, version suggestion, release notes from the whys."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..gitutil import GitError, commit_identity_args, commit_paths, git, remote_url
from ..history import why_of
from ..lint import share
from ..textutil import tokens
from ..wsgit import write_text
from .manage import PackError, latest
from .store import PACK_FILE, bump, open_pack


def _changes(ps, last_tag: str | None) -> tuple[list[dict], dict[str, str]]:
    """Commits since the last release touching the pack, and file status per path (A/M/D)."""
    if not ps.repo:
        return [], {}
    scope = ["--", ps.subdir or "."]
    rng = f"{last_tag}..HEAD" if last_tag else "HEAD"
    out = git(["log", "--format=%H%x1f%s%x1f%b%x1e", rng, *scope], cwd=ps.repo, check=False)
    commits = []
    for rec in filter(None, (r.strip() for r in out.split("\x1e"))):
        sha, subject, body = (rec.split("\x1f") + ["", ""])[:3]
        if subject.startswith("Release "):
            continue
        commits.append({"sha": sha[:7], "subject": subject, "why": why_of(body)})
    status = {}
    if last_tag:
        for line in git(["diff", "--name-status", last_tag, "HEAD", *scope], cwd=ps.repo).splitlines():
            code, _, name = line.partition("\t")
            rel = name[len(ps.subdir) + 1:] if ps.subdir else name
            if rel != PACK_FILE:
                status[rel] = code[0]
    return commits, status


def suggest(last: str | None, status: dict[str, str], has_commits: bool) -> str | None:
    if not last:
        return "0.1.0"
    if not has_commits and not status:
        return None
    codes = set(status.values())
    level = "major" if "D" in codes else "minor" if "A" in codes else "patch"
    return bump(last, level)


def my_packs(ws_root: Path, folders: list[str]) -> list[dict]:
    out = []
    for folder in folders:
        try:
            ps = open_pack(ws_root, folder)
            meta, files = ps.meta(None), ps.files(None)
        except (GitError, OSError, ValueError) as e:
            out.append({"folder": folder, "error": str(e)})
            continue
        last, last_tag = latest(ps)
        commits, status = _changes(ps, last_tag)
        issues = [{"path": rel, "line": n, "severity": sev, "message": msg}
                  for rel, text in files.items() for n, sev, msg in share.scan(text)]
        out.append({"folder": folder, "name": meta.name, "description": meta.description, "version": last,
                    "rules": len(files), "tokens": sum(tokens(t) for t in files.values()),
                    "share_issues": issues, "unreleased": commits, "file_status": status,
                    "suggested": suggest(last, status, bool(commits)), "remote": remote_url(ps.repo) if ps.repo else None})
    return out


def publish(ws_root: Path, folder: str, version: str, push: bool = True) -> dict:
    ps = open_pack(ws_root, folder)
    if not ps.repo:
        raise PackError("a pack must be in a git repository to be published")
    files = ps.files(None)
    blocking = [f"{rel}:{n} {msg}" for rel, t in files.items() for n, sev, msg in share.scan(t) if sev == "error"]
    if blocking:
        raise PackError("share check failed: " + "; ".join(blocking[:5]))
    if any(t[1] == version for t in ps.tags()):
        raise PackError(f"version {version} already exists")
    last, last_tag = latest(ps)
    commits, _ = _changes(ps, last_tag)
    notes = "\n".join(f"- {c['subject']}" + (f" — {c['why']}" if c["why"] else "") for c in commits) or "- First release"
    meta_file = ps.folder / PACK_FILE
    data = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
    data["version"] = version
    write_text(meta_file, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    name = data.get("name", folder)
    commit = commit_paths(ps.repo, [meta_file.resolve().relative_to(ps.repo).as_posix()],
                          f"Release {name} {version}", f"Release notes:\n{notes}")
    tag = f"{ps.tag_prefix}{version}"
    git([*commit_identity_args(ps.repo), "tag", "-a", tag, "-m", f"{name} {version}\n\n{notes}"], cwd=ps.repo)
    result = {"version": version, "tag": tag, "commit": commit, "notes": notes, "pushed": False}
    if push and remote_url(ps.repo):
        try:
            git(["push", "-q", "origin", "HEAD", tag], cwd=ps.repo, network=True)
            result["pushed"] = True
        except GitError as e:
            result["push_error"] = str(e)
    return result
