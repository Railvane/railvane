"""Writing to the workspace: every change Railvane makes is a commit with a why."""

from __future__ import annotations

from pathlib import Path

from .gitutil import commit_paths, repo_root


class WriteError(RuntimeError):
    pass


def commit_workspace(ws_root: Path, files: list[Path], subject: str, why: str | None) -> str | None:
    """Commit files in the workspace repo. Returns the commit sha, or None when the
    workspace is not a git repository (the files are then just written)."""
    repo = repo_root(ws_root)
    if not repo:
        return None
    rel = [f.resolve().relative_to(repo).as_posix() for f in files]
    return commit_paths(repo, rel, subject, why)


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, keeping the file's existing line endings (CRLF stays CRLF)."""
    try:
        crlf = path.exists() and b"\r\n" in path.read_bytes()
        text = text.replace("\r\n", "\n")
        if crlf:
            text = text.replace("\n", "\r\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
    except OSError as e:
        raise WriteError(f"cannot write {path.name}: {e.strerror or e}. "
                         "Is the workspace mounted read-only?") from e
