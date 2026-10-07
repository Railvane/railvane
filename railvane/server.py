"""Server mode: the workspace is a git URL instead of a local folder.

Railvane clones it into its cache, pulls regularly (and on "Fetch & rescan")
and pushes every commit it makes. Nothing lives only on the server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .gitutil import GitError
from .sources import clone_or_update


@dataclass
class WorkspaceGit:
    url: str
    branch: str | None = None
    error: str | None = None

    def clone(self) -> Path:
        os.environ["RAILVANE_AUTO_PUSH"] = "1"
        return clone_or_update(self.url, self.branch, force=True, rebase=True)

    def sync(self, force: bool = False) -> None:
        """Pull remote changes (at most once a minute unless forced). Errors are kept, not raised:
        the library stays usable with the last known state."""
        try:
            clone_or_update(self.url, self.branch, force=force, rebase=True)
            self.error = None
        except GitError as e:
            self.error = f"could not pull the workspace: {e}"

    def summary(self) -> dict:
        return {"git": self.url, "branch": self.branch, "auto_push": True, "sync_error": self.error}


def from_env() -> WorkspaceGit | None:
    url = os.environ.get("RAILVANE_WORKSPACE_GIT")
    return WorkspaceGit(url, os.environ.get("RAILVANE_WORKSPACE_BRANCH") or None) if url else None
