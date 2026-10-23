import pytest
import json

from fastapi.testclient import TestClient

from railvane import __version__
from railvane.app import create_app


def client(workspace, monkeypatch, data=None, feed=None) -> TestClient:
    if data:
        monkeypatch.setenv("RAILVANE_DATA", str(data))
    if feed is not None:
        monkeypatch.setenv("RAILVANE_RELEASES_FEED", feed)
    return TestClient(create_app(workspace))


def test_health_and_info(workspace, monkeypatch):
    c = client(workspace, monkeypatch)
    health = c.get("/api/admin/health").json()
    assert health["product"] == "railvane" and health["version"] == __version__
    assert health["status"] == "ok" and health["instance"]["mode"] == "standalone"
    info = c.get("/api/admin/info").json()
    assert info["sections"] == ["overview", "usage", "audit", "link"]
    assert info["product_info"] == {"workspace": "test-ws", "storage": "local folder", "sources": 1}
    assert info["releases"]["feed"].startswith("https://")


def test_usage_counts_guardrails(workspace, monkeypatch):
    metrics = {m["key"]: m["value"] for m in client(workspace, monkeypatch).get("/api/admin/usage").json()["metrics"]}
    assert metrics["guardrails"] == 3 and metrics["from_packs"] == 0


def test_audit_is_the_git_timeline(workspace, monkeypatch):
    entries = client(workspace, monkeypatch).get("/api/admin/audit").json()["entries"]
    assert entries[0]["action"] == "commit" and entries[0]["detail"] == "init" and entries[0]["actor"] == "Test"


def test_no_users_section(workspace, monkeypatch):
    assert client(workspace, monkeypatch).get("/api/admin/users").status_code == 404


def test_instance_id_is_kept_in_the_data_dir(workspace, monkeypatch, tmp_path):
    data = tmp_path / "data"
    first = client(workspace, monkeypatch, data).get("/api/admin/health").json()["instance"]["id"]
    again = client(workspace, monkeypatch, data).get("/api/admin/health").json()["instance"]["id"]
    assert first == again
    assert json.loads((data / "instance.json").read_text())["mode"] == "standalone"
    assert not any(p.suffix == ".md" for p in data.iterdir())   # no content in the data dir


def test_feed_can_be_switched_off(workspace, monkeypatch):
    info = client(workspace, monkeypatch, feed="").get("/api/admin/info").json()
    assert info["releases"]["feed"] is None


def test_audit_sorts_by_time_across_utc_offsets(workspace, monkeypatch):
    from tests.conftest import sh, write_files
    # Later in real time, but "smaller" as text: 10:30+00:00 is after 11:00+02:00 (= 09:00 UTC)
    for date, msg in (("2026-10-07T11:00:00+02:00", "early"), ("2026-10-07T10:30:00+00:00", "late")):
        write_files(workspace, {"CLAUDE.md": f"# {msg}\n"})
        sh(workspace, "add", "-A")
        monkeypatch.setenv("GIT_AUTHOR_DATE", date)
        sh(workspace, "commit", "-q", "-m", msg)
    details = [e["detail"] for e in client(workspace, monkeypatch).get("/api/admin/audit").json()["entries"]]
    assert details.index("late") < details.index("early")


def test_link_tab_is_open_for_a_local_tool(workspace, monkeypatch):
    c = client(workspace, monkeypatch)
    assert "link" in c.get("/api/admin/info").json()["sections"]
    state = c.get("/api/admin/link").json()
    assert state["mode"] == "standalone" and state["manage"] == "open"


@pytest.mark.parametrize("password,manage", [(None, "disabled"), ("s3cret", "password")])
def test_server_mode_needs_the_admin_password(workspace, monkeypatch, password, manage):
    from fastapi import FastAPI
    from railvane.admin import admin_api
    from railvane.index import Index

    if password:
        monkeypatch.setenv("RAILVANE_ADMIN_PASSWORD", password)
    else:
        monkeypatch.delenv("RAILVANE_ADMIN_PASSWORD", raising=False)
    app = FastAPI()
    server = type("Server", (), {"error": None})()
    app.include_router(admin_api(Index(workspace), server))
    c = TestClient(app)
    assert c.get("/api/admin/link").json()["manage"] == manage
    assert c.post("/api/admin/link/start", json={"hub_url": "https://hub.test"}).status_code == 403
