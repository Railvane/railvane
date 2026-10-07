"""Write several files into one source repository as one change: a direct commit, or (for git
sources) a branch, push and pull request. Used by edit, split and copy sync."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import github
from .gitutil import GitError, commit_paths, git, github_slug, rel_to_repo, remote_url, repo_root
from .wsgit import WriteError, push_if_enabled, write_text


class RepoWriteError(RuntimeError):
    """A problem the user can fix (read-only source, PR not possible, ...)."""


def branch_name(hint: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", PurePosixPath(hint).stem.lower()).strip("-")[:40] or "edit"
    return f"railvane/{stem}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"


def commit_files(src, files: dict[Path, str], subject: str, why: str | None, mode: str = "commit") -> dict:
    if src.readonly:
        raise RepoWriteError(f"source {src.id} is read-only — make it editable under Repositories first")
    if not files:
        return {"mode": "none", "commit": None}
    if src.kind == "path":
        if mode != "commit":
            raise RepoWriteError("pull requests are only available for git sources")
        for path, text in files.items():
            write_text(path, text)
        repo = repo_root(src.root)
        if not repo:
            return {"mode": "write", "commit": None}
        sha = commit_paths(repo, [rel_to_repo(repo, p) for p in files], subject, why)
        return {"mode": "commit", "commit": sha, "pushed": push_if_enabled(repo)}
    return _commit_git(src.root, files, subject, why, mode)


def _commit_git(repo: Path, files: dict[Path, str], subject: str, why: str | None, mode: str) -> dict:
    rels = [rel_to_repo(repo, p) for p in files]
    base = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()
    if mode == "commit":
        for path, text in files.items():
            write_text(path, text)
        sha = commit_paths(repo, rels, subject, why)
        try:
            git(["push", "-q", "origin", f"HEAD:{base}"], cwd=repo, network=True)
        except GitError as e:
            git(["reset", "-q", "--hard", "HEAD~1"], cwd=repo)
            raise WriteError(f"push failed, nothing changed: {e}") from e
        return {"mode": "commit", "commit": sha, "pushed": True}

    branch = branch_name(rels[0])
    git(["checkout", "-q", "-b", branch], cwd=repo)
    try:
        for path, text in files.items():
            write_text(path, text)
        sha = commit_paths(repo, rels, subject, why)
        git(["push", "-q", "-u", "origin", branch], cwd=repo, network=True)
    finally:
        git(["checkout", "-q", "-f", base], cwd=repo)  # the cache clone always returns to its base
    slug = github_slug(remote_url(repo))
    result = {"mode": "pr", "commit": sha, "branch": branch, "url": None}
    body = (f"Why: {why}\n\n" if why else "") + "_Opened via Railvane_"
    if slug and github.token():
        result["url"] = github.create_pull(slug, branch, base, subject, body)
    elif slug:
        result["url"] = github.compare_url(slug, base, branch)
    return result
