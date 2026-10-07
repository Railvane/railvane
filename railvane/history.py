"""History straight from git: per file, across the workspace, diffs and reverts."""

from __future__ import annotations

import re
from pathlib import Path

from .gitutil import RS, US, GitError, commit_identity_args, git

WHY = re.compile(r"^Why:\s*(.+(?:\n(?!\S+:).+)*)", re.MULTILINE)
FORMAT = f"--format={RS}%H{US}%aI{US}%an{US}%s{US}%b{US}"


def why_of(body: str) -> str | None:
    m = WHY.search(body or "")
    return " ".join(m.group(1).split()) if m else None


def _parse(out: str) -> list[dict]:
    commits = []
    for record in out.split(RS)[1:]:
        parts = record.split(US)
        if len(parts) < 6:
            continue
        sha, date, author, subject, body, names = parts[:6]
        commits.append({
            "sha": sha, "short": sha[:7], "date": date, "author": author, "subject": subject,
            "why": why_of(body), "files": [n.strip() for n in names.strip().splitlines() if n.strip()],
        })
    return commits


def file_history(repo: Path, rel_path: str, limit: int = 50) -> list[dict]:
    out = git(["log", "--follow", f"-n{limit}", FORMAT, "--name-only", "--", rel_path], cwd=repo, check=False)
    return _parse(out)


def repo_log(repo: Path, rel_paths: list[str], limit: int = 50) -> list[dict]:
    if not rel_paths:
        return []
    out = git(["log", f"-n{limit}", FORMAT, "--name-only", "--", *rel_paths], cwd=repo, check=False)
    return _parse(out)


def _check_sha(sha: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        raise GitError(f"not a commit id: {sha}")
    return sha


def show_diff(repo: Path, sha: str, rel_path: str | None = None) -> str:
    args = ["show", "--format=", "--no-color", "--no-ext-diff", _check_sha(sha)]
    return git(args + (["--", rel_path] if rel_path else []), cwd=repo)


def file_at(repo: Path, sha: str, rel_path: str) -> str:
    return git(["show", f"{_check_sha(sha)}:{rel_path}"], cwd=repo)


def revert(repo: Path, sha: str, why: str) -> str:
    """Revert a commit as a new commit carrying a why. Aborts cleanly on conflicts."""
    sha = _check_sha(sha)
    subject = git(["log", "-1", "--format=%s", sha], cwd=repo).strip()
    try:
        git(["revert", "--no-commit", sha], cwd=repo)
    except GitError as e:
        git(["revert", "--abort"], cwd=repo, check=False)
        raise GitError(f"cannot revert {sha[:7]} cleanly: {e}") from e
    message = f'Revert "{subject}"\n\nWhy: {why.strip()}\n\nVia Railvane'
    git([*commit_identity_args(repo), "commit", "-q", "-m", message], cwd=repo)
    return git(["rev-parse", "HEAD"], cwd=repo).strip()
