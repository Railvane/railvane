"""Light edits: write a guardrail and record it in git, as a direct commit or a pull request.

Local folders: direct commit in the repository that contains the file (never a
branch switch in your working copy). Git sources (Railvane's own clone): direct
commit + push, or a branch + push + pull request.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import github
from .gitutil import GitError, commit_paths, git, github_slug, rel_to_repo, remote_url, repo_root
from .index import Entry
from .sources import ResolvedSource
from .textutil import sha
from .wsgit import WriteError, push_if_enabled, write_text


class EditError(RuntimeError):
    """Problem the user can fix (conflict, read-only source, missing why)."""


def _branch_name(path: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", PurePosixPath(path).stem.lower()).strip("-")[:40] or "edit"
    return f"railvane/{stem}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"


def save(entry: Entry, src: ResolvedSource, text: str, base_hash: str, why: str,
         mode: str = "commit", subject: str | None = None) -> dict:
    if entry.readonly or src.readonly:
        raise EditError("this source is read-only")
    if not why or not why.strip():
        raise EditError("say why you change this guardrail — it becomes part of its history")
    file = Path(entry.abs_path)
    current = file.read_text(encoding="utf-8", errors="replace")
    if sha(current) != base_hash:
        raise EditError("the file changed since you opened it; reload and try again")
    if text == current:
        raise EditError("nothing changed")
    subject = (subject or f"Update {entry.title}").strip()[:120]

    if src.kind == "path":
        if mode != "commit":
            raise EditError("pull requests are only available for git sources")
        write_text(file, text)
        repo = repo_root(file)
        if not repo:
            return {"mode": "write", "commit": None}
        sha_ = commit_paths(repo, [rel_to_repo(repo, file)], subject, why)
        return {"mode": "commit", "commit": sha_, "pushed": push_if_enabled(repo)}
    return _save_git(src, file, text, subject, why, mode)


def _save_git(src: ResolvedSource, file: Path, text: str, subject: str, why: str, mode: str) -> dict:
    repo = src.root
    rel = rel_to_repo(repo, file)
    base = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()
    if mode == "commit":
        write_text(file, text)
        sha_ = commit_paths(repo, [rel], subject, why)
        try:
            git(["push", "-q", "origin", f"HEAD:{base}"], cwd=repo, network=True)
        except GitError as e:
            git(["reset", "-q", "--hard", "HEAD~1"], cwd=repo)
            raise WriteError(f"push failed, nothing changed: {e}") from e
        return {"mode": "commit", "commit": sha_, "pushed": True}

    branch = _branch_name(rel)
    git(["checkout", "-q", "-b", branch], cwd=repo)
    try:
        write_text(file, text)
        sha_ = commit_paths(repo, [rel], subject, why)
        git(["push", "-q", "-u", "origin", branch], cwd=repo, network=True)
    finally:
        git(["checkout", "-q", "-f", base], cwd=repo)  # the cache clone always returns to its base
    slug = github_slug(remote_url(repo))
    result = {"mode": "pr", "commit": sha_, "branch": branch, "url": None}
    if slug and github.token():
        result["url"] = github.create_pull(slug, branch, base, subject, f"Why: {why}\n\n_Opened via Railvane_")
    elif slug:
        result["url"] = github.compare_url(slug, base, branch)
    return result
