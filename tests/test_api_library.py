import yaml
from fastapi.testclient import TestClient

from railvane.app import create_app
from tests.conftest import sh


def client(ws):
    return TestClient(create_app(ws))


def test_library(workspace):
    body = client(workspace).get("/api/library").json()
    assert len(body["entries"]) == 3
    assert "text" not in body["entries"][0]
    assert body["facets"]["visibility"]["shared"] == 1
    assert body["sources"][0]["id"] == "test-ws"


def test_file_and_404(workspace):
    c = client(workspace)
    body = c.get("/api/file", params={"id": "test-ws/CLAUDE.md"}).json()
    assert body["text"].startswith("# Project rules")
    assert c.get("/api/file", params={"id": "nope"}).status_code == 404


def test_search(workspace):
    body = client(workspace).get("/api/search", params={"q": "powershell"}).json()
    assert body["results"][0]["id"] == "test-ws/CLAUDE.md"


def test_classify_review_and_confirm(workspace):
    c = client(workspace)
    rows = c.get("/api/classify").json()["rows"]
    assert rows[0]["confirmed"] is False          # unconfirmed first
    r = c.post("/api/classify/confirm", json={"why": "Reviewed after import", "items": [
        {"id": "test-ws/CLAUDE.md", "type": "project-rules", "area": "coding",
         "visibility": "private", "owner": "@bart"}]})
    assert r.status_code == 200 and r.json()["commit"]
    log = sh(workspace, "log", "-1", "--format=%s%n%b")
    assert "Confirm metadata for 1 guardrail" in log and "Why: Reviewed after import" in log
    entry = c.get("/api/file", params={"id": "test-ws/CLAUDE.md"}).json()
    assert entry["confirmed"] and entry["area"] == "coding"


def test_confirm_rejects_unknown_area(workspace):
    r = client(workspace).post("/api/classify/confirm", json={"items": [
        {"id": "test-ws/CLAUDE.md", "type": "project-rules", "area": "nope", "visibility": "private", "owner": "x"}]})
    assert r.status_code == 422


def test_add_source(workspace, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    c = client(workspace)
    r = c.post("/api/sources", json={"path": "../other"})
    assert r.status_code == 200 and r.json()["commit"]
    cfg = yaml.safe_load((workspace / "railvane.yaml").read_text(encoding="utf-8"))
    assert cfg["sources"][-1] == {"path": "../other", "readonly": True}
    ids = [e["id"] for e in c.get("/api/library").json()["entries"]]
    assert "other/AGENTS.md" in ids


def test_write_on_readonly_folder_gives_409(workspace, monkeypatch):
    import railvane.manifest as m

    def boom(*a, **k):
        raise PermissionError(13, "Read-only file system")
    monkeypatch.setattr(m.Path, "write_text", boom)
    r = client(workspace).post("/api/classify/confirm", json={"items": [
        {"id": "test-ws/CLAUDE.md", "type": "project-rules", "area": "coding", "visibility": "private", "owner": "x"}]})
    assert r.status_code == 409
