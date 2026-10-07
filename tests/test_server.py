import subprocess

import pytest
from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.cli import main
from railvane.server import WorkspaceGit
from tests.conftest import CLAUDE, make_repo, sh, write_files


@pytest.fixture
def remote(tmp_path, monkeypatch):
    """A bare 'GitHub' repository holding the workspace, plus a second clone acting as your laptop."""
    monkeypatch.setenv("RAILVANE_CACHE", str(tmp_path / "cache"))
    monkeypatch.delenv("RAILVANE_AUTO_PUSH", raising=False)
    seed = make_repo(tmp_path / "seed", {
        "railvane.yaml": "name: team\nsources:\n  - path: .\n  - path: /does/not/exist/on/server\n    name: memory\n",
        "CLAUDE.md": CLAUDE,
    })
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(bare)], check=True)
    laptop = tmp_path / "laptop"
    subprocess.run(["git", "clone", "-q", str(bare), str(laptop)], check=True)
    sh(laptop, "config", "user.email", "me@example.com")
    sh(laptop, "config", "user.name", "Me")
    yield bare, laptop
    monkeypatch.delenv("RAILVANE_AUTO_PUSH", raising=False)


def client(bare):
    return TestClient(create_app(workspace_git=WorkspaceGit(bare.as_posix())))


def test_edits_are_pushed(remote):
    bare, laptop = remote
    c = client(bare)
    f = c.get("/api/file", params={"id": "team/CLAUDE.md"}).json()
    r = c.put("/api/file", json={"id": "team/CLAUDE.md", "text": "# Project rules\n\n- Be kind.\n",
                                 "base_hash": f["hash"], "why": "Shorter"})
    assert r.status_code == 200 and r.json()["pushed"]
    assert "Be kind" in sh(bare, "show", "main:CLAUDE.md")

    r = c.post("/api/classify/confirm", json={"items": [{"id": "team/CLAUDE.md", "type": "project-rules",
                                                         "area": "coding", "visibility": "shared", "owner": "@me"}]})
    assert r.status_code == 200
    assert "team/CLAUDE.md" in sh(bare, "show", "main:.railvane/manifest.yaml")


def test_changes_from_elsewhere_are_pulled(remote):
    bare, laptop = remote
    c = client(bare)
    write_files(laptop, {"AGENTS.md": "# Agents\n\nPushed from my laptop.\n"})
    sh(laptop, "add", "-A")
    sh(laptop, "commit", "-qm", "Add agents file")
    sh(laptop, "push", "-q", "origin", "main")
    assert "team/AGENTS.md" not in {e["id"] for e in c.get("/api/library").json()["entries"]}
    c.post("/api/refresh")
    assert "team/AGENTS.md" in {e["id"] for e in c.get("/api/library").json()["entries"]}


def test_push_rebases_when_remote_moved(remote):
    bare, laptop = remote
    c = client(bare)
    write_files(laptop, {"other.md": "# Other\n"})
    sh(laptop, "add", "-A")
    sh(laptop, "commit", "-qm", "Laptop change")
    sh(laptop, "push", "-q", "origin", "main")   # the server does not know this commit yet
    f = c.get("/api/file", params={"id": "team/CLAUDE.md"}).json()
    r = c.put("/api/file", json={"id": "team/CLAUDE.md", "text": "# Rebased\n", "base_hash": f["hash"], "why": "w"})
    assert r.status_code == 200
    log = sh(bare, "log", "--format=%s", "main")
    assert log.splitlines()[:2] == ["Update Project rules", "Laptop change"]


def test_local_only_source_is_not_available_here(remote):
    bare, _ = remote
    src = {s["id"]: s for s in client(bare).get("/api/library").json()["sources"]}
    assert src["memory"]["available"] is False and "not found on this machine" in src["memory"]["error"]
    body = client(bare).get("/api/library").json()
    assert body["server"]["git"] == bare.as_posix() and body["server"]["auto_push"]


def test_cli_rejects_unreachable_git(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RAILVANE_CACHE", str(tmp_path / "cache"))
    assert main(["serve", "--git", (tmp_path / "missing.git").as_posix()]) == 2
    assert "railvane:" in capsys.readouterr().err
