from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.gitutil import repo_info
from tests.conftest import sh


def test_repo_info(workspace):
    info = repo_info(workspace, wait=True)
    assert info["name"] == "ws" and info["branch"] == "main" and info["remote"] is None
    assert info["head"]["subject"] == "init" and info["uncommitted"] == 0
    (workspace / "new.md").write_text("x", encoding="utf-8")
    assert repo_info(workspace, wait=True)["uncommitted"] == 1
    assert repo_info(workspace / "memory")["subdir"] == "memory"


def test_remote_is_shown_without_credentials(workspace):
    sh(workspace, "remote", "add", "origin", "https://user:secret@github.com/Org/rules.git")
    info = repo_info(workspace, wait=True)
    assert info["remote"] == "https://github.com/Org/rules.git"
    assert info["web"] == "https://github.com/Org/rules"


def test_library_shows_repos(workspace, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (workspace / "railvane.yaml").write_text("name: test-ws\nsources:\n  - path: .\n  - path: ../plain\n",
                                             encoding="utf-8")
    body = TestClient(create_app(workspace)).get("/api/library").json()
    assert body["workspace_repo"]["name"] == "ws"
    repos = {s["id"]: s["repo"] for s in body["sources"]}
    assert repos["test-ws"]["branch"] == "main"
    assert repos["plain"] is None   # a plain folder, not in git


def test_display_path(monkeypatch):
    from railvane.gitutil import display_path
    monkeypatch.setenv("RAILVANE_PATH_MAP", "/workspace=C:/Projects/rules;/sources/hp=C:/Projects/homeplatform")
    assert display_path("/workspace") == "C:/Projects/rules"
    assert display_path("/sources/hp/sub") == "C:/Projects/homeplatform/sub"
    assert display_path("/other") == "/other"   # unmapped paths stay as they are
