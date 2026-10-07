import os
import subprocess
from pathlib import Path

import pytest

os.environ.update({
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
})


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_repo(path: Path, files: dict[str, str], message: str = "init") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        sh(path, "init", "-q", "-b", "main")
        sh(path, "config", "user.email", "test@example.com")
        sh(path, "config", "user.name", "Test")
    write_files(path, files)
    sh(path, "add", "-A")
    sh(path, "commit", "-q", "-m", message)
    return path


def write_files(path: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8", newline="\n")


DEPLOY = """---
type: memory
area: deploy
visibility: shared
owner: "@bart"
tags: [deploy]
---
# Deploy agreements

Never deploy without an explicit order. See [[branching]].
"""

BRANCHING = """---
name: branching
description: Always develop to main.
metadata:
  type: feedback
---
Always merge develop into main, never the other way. Test on acc first.
"""

CLAUDE = """# Project rules

- Code in English.
- Never deploy without an explicit order.
- Shell is PowerShell 5.1. See [[missing-note]].
"""


@pytest.fixture
def workspace(tmp_path) -> Path:
    """A git workspace with three guardrails: valid frontmatter, foreign frontmatter, none."""
    return make_repo(tmp_path / "ws", {
        "railvane.yaml": "version: 1\nname: test-ws\ndefaults:\n  owner: '@bart'\n",
        "memory/feedback_deploy.md": DEPLOY,
        "memory/branching.md": BRANCHING,
        "CLAUDE.md": CLAUDE,
    })
