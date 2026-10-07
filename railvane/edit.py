"""Light edits: write a guardrail and record it in git, as a direct commit or a pull request.

Local folders: direct commit in the repository that contains the file (never a branch switch
in your working copy). Git sources (Railvane's own clone): commit + push, or branch + PR.
"""

from __future__ import annotations

from pathlib import Path

from .index import Entry
from .repowrite import RepoWriteError, commit_files
from .sources import ResolvedSource
from .textutil import sha


class EditError(RuntimeError):
    """Problem the user can fix (conflict, read-only source, missing why)."""


def save(entry: Entry, src: ResolvedSource, text: str, base_hash: str, why: str,
         mode: str = "commit", subject: str | None = None) -> dict:
    if entry.copy_of:
        raise EditError(f"this is a copy of {entry.copy_of} — edit the master and sync the copies")
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
    try:
        return commit_files(src, {file: text}, subject, why, mode)
    except RepoWriteError as e:
        raise EditError(str(e)) from e
