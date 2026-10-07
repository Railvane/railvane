"""Thin wrapper around the git CLI. Git is Railvane's only storage engine."""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

US, RS = "\x1f", "\x1e"  # unit / record separators for parseable git output


class GitError(RuntimeError):
    pass


def _auth_args(url_or_cwd: str | None) -> list[str]:
    """Authenticate https GitHub access with RAILVANE_GITHUB_TOKEN, if set."""
    token = os.environ.get("RAILVANE_GITHUB_TOKEN")
    if not token:
        return []
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return ["-c", f"http.https://github.com/.extraheader=Authorization: Basic {basic}"]


def _identity_args() -> list[str]:
    args = []
    if name := os.environ.get("RAILVANE_GIT_NAME"):
        args += ["-c", f"user.name={name}"]
    if email := os.environ.get("RAILVANE_GIT_EMAIL"):
        args += ["-c", f"user.email={email}"]
    return args


def git(args: list[str], cwd: str | Path | None = None, check: bool = True,
        timeout: int = 120, network: bool = False) -> str:
    cmd = ["git", "-c", "core.quotepath=off", *_identity_args()]
    if network:
        cmd += _auth_args(None)
    cmd += args
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as e:
        raise GitError(f"git {args[0]} timed out") from e
    out = res.stdout.decode("utf-8", "replace")
    if check and res.returncode != 0:
        raise GitError(res.stderr.decode("utf-8", "replace").strip() or f"git {args[0]} failed")
    return out


def repo_root(path: str | Path) -> Path | None:
    """Top folder of the git repository containing path, or None."""
    p = Path(path)
    cwd = p if p.is_dir() else p.parent
    try:
        out = git(["rev-parse", "--show-toplevel"], cwd=cwd, timeout=20).strip()
    except (GitError, FileNotFoundError, NotADirectoryError):
        return None
    return Path(out).resolve() if out else None


def rel_to_repo(repo: Path, file: Path) -> str:
    return file.resolve().relative_to(repo).as_posix()


def last_changes(repo: Path, rel_paths: list[str]) -> dict[str, str]:
    """ISO date of the last commit per file (one git call for all files)."""
    if not rel_paths:
        return {}
    out = git(["log", f"--format={RS}%aI", "--name-only", "--", *rel_paths], cwd=repo, check=False)
    dates: dict[str, str] = {}
    wanted = set(rel_paths)
    for record in out.split(RS)[1:]:
        lines = record.strip().splitlines()
        if not lines:
            continue
        date = lines[0].strip()
        for name in lines[1:]:
            name = name.strip()
            if name in wanted and name not in dates:
                dates[name] = date
        if len(dates) == len(wanted):
            break
    return dates


def is_clean(repo: Path, rel_path: str) -> bool:
    return git(["status", "--porcelain", "--", rel_path], cwd=repo).strip() == ""


def commit_paths(repo: Path, rel_paths: list[str], subject: str, why: str | None = None) -> str:
    """Commit only the given paths (other staged/unstaged work is left alone)."""
    message = subject + (f"\n\nWhy: {why.strip()}" if why and why.strip() else "")
    message += "\n\nVia Railvane"
    git(["add", "--", *rel_paths], cwd=repo)
    git([*commit_identity_args(repo), "commit", "-q", "--only", "-m", message, "--", *rel_paths], cwd=repo)
    return git(["rev-parse", "HEAD"], cwd=repo).strip()


def commit_identity_args(repo: Path) -> list[str]:
    """Fallback identity when neither RAILVANE_GIT_* nor git config provide one."""
    if has_identity(repo):
        return []
    return ["-c", "user.name=Railvane", "-c", "user.email=railvane@localhost"]


def has_identity(repo: Path) -> bool:
    if os.environ.get("RAILVANE_GIT_EMAIL"):
        return True
    return bool(git(["config", "user.email"], cwd=repo, check=False).strip())


def remote_url(repo: Path) -> str | None:
    out = git(["remote", "get-url", "origin"], cwd=repo, check=False).strip()
    return out or None


def github_slug(url: str | None) -> str | None:
    """'owner/name' for a GitHub remote URL, else None."""
    if not url:
        return None
    if url.startswith("git@github.com:"):
        path = url.split(":", 1)[1]
    else:
        parsed = urlparse(url)
        if parsed.hostname != "github.com":
            return None
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git")
    return path if path.count("/") == 1 else None
