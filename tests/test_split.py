import yaml
from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.split import plan, sections
from tests.conftest import make_repo, sh, write_files

BIG = """# Project — agreements

Intro line that stays.

## Deploy

- Deploys run through GitHub Actions: `develop` to acceptance on port 8081.
- Never deploy on Friday.

## Technical agreements

### Language
- Code in English, comments in Dutch.

### PowerShell
- PowerShell 5.1: no `&&`, use `;`.

## Caddy reset

```bash
ssh admin@10.0.0.5
docker compose up -d caddy
```
"""


def test_sections_split_containers_into_sub_sections():
    preamble, parts = sections(BIG)
    assert preamble.startswith("# Project") and "Intro line" in preamble
    assert [p["heading"] for p in parts] == ["Deploy", "Language", "PowerShell", "Caddy reset"]
    assert parts[1]["parent"] == "Technical agreements"


def test_suggestions():
    s = {p["heading"]: p["suggestion"] for p in plan(BIG)["parts"]}
    assert s["Deploy"]["action"] == "project"        # port number: project specific
    assert s["Language"]["action"] == "shared"
    assert s["Caddy reset"]["action"] == "skill"     # a short command procedure
    assert s["PowerShell"]["filename"] == "powershell.md"


def setup(tmp_path):
    proj = make_repo(tmp_path / "proj", {"CLAUDE.md": BIG})
    ws = make_repo(tmp_path / "ws", {"railvane.yaml": "name: ws\nsources:\n  - path: .\n    include: ['guardrails/**/*.md']\n"
                                                      "  - path: ../proj\n    name: proj\n"})
    return proj, ws, TestClient(create_app(ws))


def apply(c, choices):
    p = c.get("/api/split/plan", params={"id": "proj/CLAUDE.md"}).json()
    keys = {part["heading"]: part["key"] for part in p["parts"]}
    return c.post("/api/split/apply", json={"id": "proj/CLAUDE.md", "why": "Smaller, reusable rules",
                                            "choices": {keys[h]: v for h, v in choices.items()}})


CHOICES = {"Deploy": {"action": "project", "area": "deploy"},
           "Language": {"action": "shared", "area": "coding"},
           "PowerShell": {"action": "keep"},
           "Caddy reset": {"action": "skill", "area": "incident"}}


def test_apply_across_repositories(tmp_path):
    proj, ws, c = setup(tmp_path)
    r = apply(c, CHOICES)
    assert r.status_code == 200, r.text
    main = (proj / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Intro line" in main and "@.claude/guardrails/deploy.md" in main
    assert "## Technical agreements\n\n@.claude/guardrails/shared/language.md" in main
    assert "PowerShell 5.1" in main                         # kept inline
    assert "- `caddy-reset` — Caddy reset" in main
    assert (proj / ".claude/guardrails/deploy.md").read_text(encoding="utf-8").startswith("# Deploy\n")
    skill = (proj / ".claude/skills/caddy-reset/SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: caddy-reset\ndescription:") and "docker compose" in skill
    assert (ws / "guardrails/shared/language.md").read_text(encoding="utf-8") == \
        (proj / ".claude/guardrails/shared/language.md").read_text(encoding="utf-8")
    cfg = yaml.safe_load((ws / "railvane.yaml").read_text(encoding="utf-8"))
    assert cfg["copies"] == [{"master": "guardrails/shared/language.md", "source": "proj",
                              "path": ".claude/guardrails/shared/language.md"}]
    assert "Why: Smaller, reusable rules" in sh(proj, "log", "-1", "--format=%b")
    assert "Shared guardrails from proj/CLAUDE.md" in sh(ws, "log", "-1", "--format=%s")

    lib = {e["id"]: e for e in c.get("/api/library").json()["entries"]}
    copy = lib["proj/.claude/guardrails/shared/language.md"]
    assert copy["copy_of"] == "ws/guardrails/shared/language.md" and copy["copy_status"] == "in_sync"
    assert copy["confirmed"] and copy["area"] == "coding"
    assert lib["proj/CLAUDE.md"]["type"] == "index"
    assert lib["proj/.claude/skills/caddy-reset/SKILL.md"]["type"] == "skill"
    rules = {f["rule"] for f in c.get("/api/quality").json()["findings"]}
    assert "duplicate-rule" not in rules and "copy-drift" not in rules


def test_drift_sync_and_copy_edit_guard(tmp_path):
    proj, ws, c = setup(tmp_path)
    apply(c, CHOICES)
    write_files(ws, {"guardrails/shared/language.md": "# Language\n- Code in English. Comments too.\n"})
    sh(ws, "commit", "-qam", "Tighten language rule")
    c.post("/api/refresh")
    copy_id = "proj/.claude/guardrails/shared/language.md"
    assert c.get("/api/file", params={"id": copy_id}).json()["copy_status"] == "drift"
    assert any(f["rule"] == "copy-drift" for f in c.get("/api/quality").json()["findings"])
    f = c.get("/api/file", params={"id": copy_id}).json()
    r = c.put("/api/file", json={"id": copy_id, "text": "x", "base_hash": f["hash"], "why": "w"})
    assert r.status_code == 409 and "copy of" in r.json()["detail"]

    r = c.post("/api/copies/sync", json={})
    assert r.status_code == 200 and r.json()["synced"]["proj"]["commit"]
    assert "Comments too" in (proj / ".claude/guardrails/shared/language.md").read_text(encoding="utf-8")
    assert c.get("/api/copies").json()["copies"][0]["status"] == "in_sync"


def test_readonly_source_blocks_split_until_switched(tmp_path):
    proj, ws, c = setup(tmp_path)
    assert c.post("/api/sources/readonly", json={"id": "proj", "readonly": True}).status_code == 200
    r = apply(c, CHOICES)
    assert r.status_code == 409 and "read-only" in r.json()["detail"]
    c.post("/api/sources/readonly", json={"id": "proj", "readonly": False})
    assert apply(c, CHOICES).status_code == 200


def test_split_inside_the_workspace_is_one_commit(tmp_path):
    ws = make_repo(tmp_path / "ws", {"railvane.yaml": "name: ws\ninclude: ['**/*.md']\n", "AGENTS.md": BIG})
    c = TestClient(create_app(ws))
    before = int(sh(ws, "rev-list", "--count", "HEAD"))
    p = c.get("/api/split/plan", params={"id": "ws/AGENTS.md"}).json()
    key = next(x["key"] for x in p["parts"] if x["heading"] == "Language")
    r = c.post("/api/split/apply", json={"id": "ws/AGENTS.md", "why": "w", "choices": {key: {"action": "shared", "area": "coding"}}})
    assert r.status_code == 200, r.text
    assert int(sh(ws, "rev-list", "--count", "HEAD")) == before + 1
    assert "@guardrails/shared/language.md" in (ws / "AGENTS.md").read_text(encoding="utf-8")
    assert "copies" not in yaml.safe_load((ws / "railvane.yaml").read_text(encoding="utf-8"))
