"""Thin wrapper around the git CLI. Git is Railvane's only storage engine."""

from __future__ import annotations

import base64
import logging
import os
import subprocess
import threading
import time
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
    """ISO date of the last commit per file. One bounded call over recent history, then a
    'log -1' per file that was not touched recently (walking all history is slow)."""
    if not rel_paths:
        return {}
    repo, rev = history_repo(repo)
    out = git(["log", "-n300", f"--format={RS}%aI", "--name-only", rev, "--", *rel_paths], cwd=repo, check=False)
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
    for name in [p for p in rel_paths if p not in dates][:30]:
        date = git(["log", "-1", "--format=%aI", rev, "--", name], cwd=repo, check=False).strip()
        if date:
            dates[name] = date
    return dates


def is_clean(repo: Path, rel_path: str) -> bool:
    return git(["status", "--porcelain", "--", rel_path], cwd=repo).strip() == ""


def commit_paths(repo: Path, rel_paths: list[str], subject: str, why: str | None = None) -> str:
    """Commit only the given paths (other staged/unstaged work is left alone)."""
    message = subject + (f"\n\nWhy: {why.strip()}" if why and why.strip() else "")
    message += "\n\nVia Railvane"
    git(["add", "--", *rel_paths], cwd=repo)
    git([*commit_identity_args(repo), "commit", "-q", "--only", "-m", message, "--", *rel_paths], cwd=repo)
    forget_status(repo)
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


def _without_credentials(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return parsed._replace(netloc=parsed.hostname + (f":{parsed.port}" if parsed.port else "")).geturl()
    return url


def display_path(path: str | Path | None) -> str | None:
    """Translate a container path to the host path the user knows, using
    RAILVANE_PATH_MAP="/workspace=C:/Projects/rules;/sources/x=C:/Projects/x"."""
    if path is None:
        return None
    text = Path(path).as_posix()
    pairs = [p.split("=", 1) for p in os.environ.get("RAILVANE_PATH_MAP", "").split(";") if "=" in p]
    for inner, outer in sorted(pairs, key=lambda x: -len(x[0])):
        inner = inner.rstrip("/")
        if text == inner or text.startswith(inner + "/"):
            return outer.rstrip("/\\") + text[len(inner):]
    return str(path)


def repo_info(path: str | Path, wait: bool = False) -> dict | None:
    """What the UI shows about a repository: name, branch, remote, last commit, uncommitted changes."""
    repo = repo_root(path)
    if not repo:
        return None
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, check=False).strip() or None
    remote = _without_credentials(remote_url(repo))
    slug = github_slug(remote)
    head = git(["log", "-1", f"--format=%h{US}%s{US}%aI"], cwd=repo, check=False).strip()
    sha, subject, date = (head.split(US) + ["", "", ""])[:3]
    sub = Path(path).resolve()
    return {
        # Name from the remote, else from the host path (in a container the folder is just /workspace
        # or a cache folder)
        "name": (remote.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1].rsplit(":", 1)[-1] if remote
                 else Path(display_path(repo)).name or repo.name), "root": str(repo), "display_root": display_path(repo),
        "branch": branch, "remote": remote,
        "web": f"https://github.com/{slug}" if slug else None,
        "subdir": sub.relative_to(repo).as_posix() if sub != repo and sub.is_relative_to(repo) else None,
        "head": {"sha": sha, "subject": subject, "date": date} if sha else None,
        "uncommitted": uncommitted(repo, wait=wait),
    }


# `git status` must stat every file: seconds on a Docker mount of a Windows folder.
# It is computed in the background and cached; the UI shows the last known count.
STATUS_TTL = 120
_status: dict[str, tuple[float, int | None]] = {}
_status_running: set[str] = set()
_status_lock = threading.Lock()


def _compute_status(repo: Path) -> None:
    out = git(["--no-optional-locks", "status", "--porcelain"], cwd=repo, check=False, timeout=300)
    with _status_lock:
        _status[str(repo)] = (time.time(), sum(1 for line in out.splitlines() if line.strip()))
        _status_running.discard(str(repo))


def uncommitted(repo: Path, wait: bool = False) -> int | None:
    """Number of uncommitted changes; None while the first count is still running."""
    key = str(repo)
    if wait:
        _compute_status(repo)
    with _status_lock:
        ts, value = _status.get(key, (0.0, None))
        if time.time() - ts > STATUS_TTL and key not in _status_running:
            _status_running.add(key)
            threading.Thread(target=_compute_status, args=(repo,), daemon=True).start()
    return value


def forget_status(repo: Path) -> None:
    """After a commit the count is outdated: recount on the next request."""
    with _status_lock:
        if str(repo) in _status:
            _status[str(repo)] = (0.0, _status[str(repo)][1])


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


# --- History mirror -------------------------------------------------------------------------
# Reading git history through a Docker mount of a Windows folder is very slow (seconds per
# `git log`). With RAILVANE_HISTORY_MIRROR=1 Railvane keeps a bare copy of such repositories in
# its cache (native file system) and runs history commands there. The working tree is still
# read from the mount. The mirror is built once in the background and fetched incrementally.

_mirror_lock = threading.Lock()
_mirror_building: set[str] = set()


def cache_dir() -> Path:
    return Path(os.environ.get("RAILVANE_CACHE") or Path.home() / ".cache" / "railvane")


def _mirror_path(repo: Path) -> Path:
    import hashlib
    return cache_dir() / "mirror" / f"{hashlib.sha1(str(repo).encode()).hexdigest()[:10]}-{repo.name}.git"


def _build_mirror(repo: Path, target: Path) -> None:
    tmp = target.with_suffix(".tmp")
    try:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        git(["clone", "-q", "--bare", "--no-local", str(repo), str(tmp)], timeout=1800)
        git(["commit-graph", "write", "--reachable", "--changed-paths"], cwd=tmp, check=False)
        tmp.rename(target)
    except (GitError, OSError) as e:
        # Retried on a later request; history keeps working from the mount meanwhile
        logging.getLogger("railvane").warning("history mirror for %s failed: %s", repo, e)
    finally:
        with _mirror_lock:
            _mirror_building.discard(str(repo))


def history_repo(repo: Path) -> tuple[Path, str]:
    """(repository to run history commands in, revision to start from)."""
    head = git(["rev-parse", "HEAD"], cwd=repo, check=False).strip() or "HEAD"
    if os.environ.get("RAILVANE_HISTORY_MIRROR", "").lower() not in ("1", "true", "yes"):
        return repo, head
    if str(repo).startswith(str(cache_dir())):
        return repo, head   # our own clones already live on a fast file system
    target = _mirror_path(repo)
    if not target.exists():
        with _mirror_lock:
            if str(repo) not in _mirror_building:
                _mirror_building.add(str(repo))
                threading.Thread(target=_build_mirror, args=(repo, target), daemon=True).start()
        return repo, head
    if head != "HEAD" and not _has_commit(target, head):   # new commits in the repo: fetch them
        git(["fetch", "-q", "--tags", str(repo), "+refs/heads/*:refs/heads/*"], cwd=target, check=False, timeout=300)
        git(["commit-graph", "write", "--reachable", "--changed-paths"], cwd=target, check=False)
        if not _has_commit(target, head):   # e.g. a detached or brand-new state: use the mount
            return repo, head
    return target, head


def _has_commit(repo: Path, sha: str) -> bool:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo, env=env,
                          capture_output=True, timeout=20).returncode == 0
