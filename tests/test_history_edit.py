import subprocess

from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.history import why_of
from tests.conftest import make_repo, sh


def client(ws):
    return TestClient(create_app(ws))


def file(c, eid):
    return c.get("/api/file", params={"id": eid}).json()


def edit(c, eid, text, why="Clearer wording", **kw):
    f = file(c, eid)
    return c.put("/api/file", json={"id": eid, "text": text, "base_hash": f["hash"], "why": why, **kw})


def test_why_of():
    assert why_of("Body\n\nWhy: because\nit matters\n\nVia Railvane") == "because it matters"
    assert why_of("no trailer") is None


def test_edit_commits_with_why_and_history_shows_it(workspace):
    c = client(workspace)
    eid = "test-ws/CLAUDE.md"
    r = edit(c, eid, "# Project rules\n\n- Code in English.\n")
    assert r.status_code == 200 and r.json()["mode"] == "commit"
    assert (workspace / "CLAUDE.md").read_text(encoding="utf-8").endswith("English.\n")
    commits = c.get("/api/history", params={"id": eid}).json()["commits"]
    assert commits[0]["subject"] == "Update Project rules" and commits[0]["why"] == "Clearer wording"
    d = c.get("/api/diff", params={"id": eid, "sha": commits[0]["sha"]}).json()["diff"]
    assert "\n-- Shell is PowerShell 5.1" in d  # removed bullet line
    old = c.get("/api/file-at", params={"id": eid, "sha": commits[1]["sha"]}).json()["text"]
    assert "PowerShell" in old


def test_edit_guards(workspace):
    c = client(workspace)
    eid = "test-ws/CLAUDE.md"
    stale = c.put("/api/file", json={"id": eid, "text": "x", "base_hash": "0" * 16, "why": "w"})
    assert stale.status_code == 409 and "changed since" in stale.json()["detail"]
    assert edit(c, eid, "x", why=" ").status_code == 409
    assert edit(c, eid, "x", mode="pr").status_code == 409  # PRs only for git sources
    (workspace / "railvane.yaml").write_text(
        "name: test-ws\nsources:\n  - path: .\n    readonly: true\n", encoding="utf-8")
    r = edit(c, eid, "x")
    assert r.status_code == 409 and "read-only" in r.json()["detail"]


def test_revert(workspace):
    c = client(workspace)
    eid = "test-ws/CLAUDE.md"
    edit(c, eid, "# Short\n")
    sha = c.get("/api/history", params={"id": eid}).json()["commits"][0]["sha"]
    r = c.post("/api/revert", json={"id": eid, "sha": sha, "why": "Too short"})
    assert r.status_code == 200
    assert "PowerShell" in (workspace / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Why: Too short" in sh(workspace, "log", "-1", "--format=%b")


def test_timeline_includes_settings(workspace):
    c = client(workspace)
    edit(c, "test-ws/CLAUDE.md", "# Changed\n")
    commits = c.get("/api/timeline").json()["commits"]
    assert commits[0]["ids"] == ["test-ws/CLAUDE.md"] and commits[0]["why"] == "Clearer wording"
    assert any(x["settings"] == ["railvane.yaml"] for x in commits)


def test_git_source_commit_and_pr(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILVANE_CACHE", str(tmp_path / "cache"))
    upstream = make_repo(tmp_path / "upstream", {"AGENTS.md": "# Agents\n\nBe brief.\n"})
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(upstream), str(bare)], check=True)
    ws = make_repo(tmp_path / "ws", {"railvane.yaml": f"sources:\n  - git: {bare.as_posix()}\n    name: team\n"})
    c = client(ws)
    eid = "team/AGENTS.md"

    r = edit(c, eid, "# Agents\n\nBe very brief.\n")
    assert r.status_code == 200 and r.json()["pushed"]
    assert "Be very brief" in sh(bare, "show", "main:AGENTS.md")

    r = edit(c, eid, "# Agents\n\nBe brief and kind.\n", mode="pr")
    body = r.json()
    assert r.status_code == 200 and body["branch"].startswith("railvane/agents-")
    assert "kind" in sh(bare, "show", f"{body['branch']}:AGENTS.md")
    assert "kind" not in sh(bare, "show", "main:AGENTS.md")
    assert "kind" not in file(c, eid)["text"]  # the clone went back to main


def test_edit_keeps_crlf(workspace):
    (workspace / "CLAUDE.md").write_bytes(b"# Project rules\r\n\r\n- Old rule.\r\n")
    c = client(workspace)
    assert edit(c, "test-ws/CLAUDE.md", "# Project rules\n\n- New rule.\n").status_code == 200
    assert (workspace / "CLAUDE.md").read_bytes() == b"# Project rules\r\n\r\n- New rule.\r\n"


def test_history_mirror(workspace, tmp_path, monkeypatch):
    import time

    from railvane import gitutil
    from railvane.history import file_history
    monkeypatch.setenv("RAILVANE_HISTORY_MIRROR", "1")
    monkeypatch.setenv("RAILVANE_CACHE", str(tmp_path / "cache"))
    assert file_history(workspace, "CLAUDE.md")[0]["subject"] == "init"   # mirror builds meanwhile
    mirror = gitutil._mirror_path(workspace)
    for _ in range(100):
        if mirror.exists():
            break
        time.sleep(0.1)
    assert gitutil.history_repo(workspace)[0] == mirror
    (workspace / "CLAUDE.md").write_text("# Changed\n", encoding="utf-8")
    sh(workspace, "commit", "-qam", "Change rules", "-m", "Why: testing the mirror")
    first = file_history(workspace, "CLAUDE.md")[0]   # the new commit is fetched into the mirror
    assert first["subject"] == "Change rules" and first["why"] == "testing the mirror"
