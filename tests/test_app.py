from fastapi.testclient import TestClient

from railvane import __version__
from railvane.app import create_app
from railvane.cli import main


def test_health(tmp_path):
    r = TestClient(create_app(tmp_path)).get("/api/health")
    assert r.json() == {"status": "ok", "version": __version__}


def test_workspace_reflects_config_changes(tmp_path):
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/workspace").json()["config_found"] is False
    (tmp_path / "railvane.yaml").write_text("name: changed\n", encoding="utf-8")
    body = client.get("/api/workspace").json()
    assert body["config_found"] is True
    assert body["config"]["name"] == "changed"


def test_schema(tmp_path):
    body = TestClient(create_app(tmp_path)).get("/api/schema").json()
    assert body["frontmatter"]["version"] == 1
    assert "incident" in body["phases"]["ops"]["areas"]


def test_cli_serve_missing_folder(tmp_path, capsys):
    assert main(["serve", str(tmp_path / "nope")]) == 2
    assert "not found" in capsys.readouterr().err


def test_app_from_env(tmp_path, monkeypatch):
    from railvane.app import app_from_env

    (tmp_path / "railvane.yaml").write_text("name: from-env\n", encoding="utf-8")
    monkeypatch.setenv("RAILVANE_WORKSPACE", str(tmp_path))
    body = TestClient(app_from_env()).get("/api/workspace").json()
    assert body["config"]["name"] == "from-env"
