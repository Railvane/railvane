import yaml
from fastapi.testclient import TestClient

from railvane.app import create_app
from tests.conftest import make_repo, sh, write_files

PACK_META = "name: team/base-rules\ndescription: Team basics\nlicense: Apache-2.0\nversion: {v}\n"


def make_pack(tmp_path):
    """Upstream pack with v1.0.0 and v1.1.0 (one rule changed with a why, one added)."""
    up = make_repo(tmp_path / "upstream", {
        "railvane-pack.yaml": PACK_META.format(v="1.0.0"),
        "README.md": "# Not a rule\n",
        "comments.md": "# Comments\n\n- Comments in English.\n",
        "deploy.md": "# Deploy\n\n- Never deploy on Friday.\n",
    })
    sh(up, "tag", "v1.0.0")
    write_files(up, {"comments.md": "# Comments\n\n- Comments in English; Dutch allowed in hobby projects.\n"})
    sh(up, "commit", "-qam", "Relax comment rule", "-m", "Why: too strict for hobby projects")
    write_files(up, {"privacy.md": "# Privacy\n\n- No production data in prompts.\n",
                     "railvane-pack.yaml": PACK_META.format(v="1.1.0")})
    sh(up, "add", "-A")
    sh(up, "commit", "-qm", "Add privacy rule", "-m", "Why: audit finding")
    sh(up, "tag", "v1.1.0")
    return up


def setup(tmp_path):
    make_pack(tmp_path)
    ws = make_repo(tmp_path / "ws", {
        "railvane.yaml": "name: ws\ncatalog: ['../upstream']\npublish: [packs/mine]\n",
        "CLAUDE.md": "# Rules\n",
        "packs/mine/railvane-pack.yaml": "name: bart/conventions\n",
        "packs/mine/git.md": "# Git\n\n- Always develop first.\n",
    })
    return ws, TestClient(create_app(ws))


def test_install_old_version_then_update_with_keep(tmp_path):
    ws, c = setup(tmp_path)
    r = c.post("/api/packs/install", json={"source": "../upstream", "version": "1.0.0"})
    assert r.status_code == 200 and r.json()["name"] == "team/base-rules"
    cfg = yaml.safe_load((ws / "railvane.yaml").read_text(encoding="utf-8"))
    assert cfg["packs"][0]["version"] == "1.0.0" and len(cfg["packs"][0]["sha"]) == 40

    ids = {e["id"] for e in c.get("/api/library").json()["entries"]}
    assert {"pack:team/base-rules/comments.md", "pack:team/base-rules/deploy.md"} <= ids
    assert not any(i.endswith("README.md") for i in ids)

    info = c.get("/api/packs").json()["packs"][0]
    assert info["update"] and info["latest"] == "1.1.0" and not info["major"]
    changes = {ch["path"]: ch for ch in info["changes"]}
    assert changes["comments.md"]["kind"] == "changed"
    assert changes["comments.md"]["why"] == ["too strict for hobby projects"]
    assert changes["privacy.md"]["kind"] == "added"

    r = c.post("/api/packs/update", json={"name": "team/base-rules", "keep": ["comments.md"], "why": "Keep strict"})
    assert r.status_code == 200 and r.json()["version"] == "1.1.0"
    comments = c.get("/api/file", params={"id": "pack:team/base-rules/comments.md"}).json()
    assert comments["overridden"] and "hobby" not in comments["text"]
    assert "pack:team/base-rules/privacy.md" in {e["id"] for e in c.get("/api/library").json()["entries"]}
    assert not c.get("/api/packs").json()["packs"][0]["update"]


def test_override_by_editing_and_drop(tmp_path):
    ws, c = setup(tmp_path)
    c.post("/api/packs/install", json={"source": "../upstream"})
    eid = "pack:team/base-rules/deploy.md"
    f = c.get("/api/file", params={"id": eid}).json()
    r = c.put("/api/file", json={"id": eid, "text": "# Deploy\n\n- Never deploy on Fridays or holidays.\n",
                                 "base_hash": f["hash"], "why": "Holidays too"})
    assert r.status_code == 200 and r.json()["mode"] == "override"
    assert (ws / ".railvane/overrides/team__base-rules/deploy.md").exists()
    assert c.get("/api/file", params={"id": eid}).json()["overridden"]
    assert c.post("/api/packs/drop-override", json={"id": eid}).status_code == 200
    assert not c.get("/api/file", params={"id": eid}).json()["overridden"]


def test_discover_and_remove(tmp_path):
    ws, c = setup(tmp_path)
    found = c.get("/api/packs/discover").json()["packs"][0]
    assert found["name"] == "team/base-rules" and found["version"] == "1.1.0" and found["rules"] == 3
    assert not found["installed"]
    c.post("/api/packs/install", json={"source": "../upstream"})
    assert c.get("/api/packs/discover").json()["packs"][0]["installed"]
    assert c.post("/api/packs/install", json={"source": "../upstream"}).status_code == 409
    assert c.post("/api/packs/remove", json={"name": "team/base-rules"}).status_code == 200
    assert c.get("/api/packs").json()["packs"] == []


def test_my_packs_and_publish(tmp_path):
    ws, c = setup(tmp_path)
    mine = c.get("/api/packs/mine").json()["packs"][0]
    assert mine["name"] == "bart/conventions" and mine["version"] is None and mine["suggested"] == "0.1.0"
    r = c.post("/api/packs/publish", json={"folder": "packs/mine", "version": "0.1.0"})
    assert r.status_code == 200 and r.json()["tag"] == "packs/mine/v0.1.0" and not r.json()["pushed"]
    assert "packs/mine/v0.1.0" in sh(ws, "tag", "-l")

    write_files(ws, {"packs/mine/new.md": "# New\n\n- A new rule.\n"})
    sh(ws, "add", "-A")
    sh(ws, "commit", "-qm", "Add new rule", "-m", "Why: needed it")
    mine = c.get("/api/packs/mine").json()["packs"][0]
    assert mine["version"] == "0.1.0" and mine["suggested"] == "0.2.0"
    assert mine["unreleased"][0]["why"] == "needed it"


def test_publish_blocked_by_secret(tmp_path):
    ws, c = setup(tmp_path)
    write_files(ws, {"packs/mine/leak.md": "# Leak\n\ntoken ghp_" + "x" * 36 + "\n"})
    r = c.post("/api/packs/publish", json={"folder": "packs/mine", "version": "0.1.0"})
    assert r.status_code == 409 and "share check failed" in r.json()["detail"]
