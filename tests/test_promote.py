from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.index import build
from tests.conftest import make_repo

FEEDBACK = """---
name: prod-gate
description: After acc, wait for an explicit go for production.
metadata:
  type: feedback
---
After a deploy to acceptance, always wait for an explicit go before production.
"""


def test_memory_subtypes(tmp_path):
    ws = make_repo(tmp_path / "ws", {
        "railvane.yaml": "name: ws\n",
        "memory/prod_gate.md": FEEDBACK,
        "memory/project_status.md": "# Status\n\nMVP done.\n",
        "memory/MEMORY.md": "- [x](prod_gate.md)\n",
    })
    e = build(ws).entries
    assert e["ws/memory/prod_gate.md"].subtype == "feedback"        # from metadata.type
    assert e["ws/memory/project_status.md"].subtype == "project"    # from the file name
    assert e["ws/memory/MEMORY.md"].subtype is None                 # an index, not a memory


def test_promote_memory_to_rule(tmp_path):
    ws = make_repo(tmp_path / "ws", {
        "railvane.yaml": "name: ws\ninclude: ['memory/*.md', 'guardrails/**/*.md']\n",
        "memory/prod_gate.md": FEEDBACK,
        "guardrails/shared/deploy.md": "# Deploy\n\n- After a deploy to acceptance, always wait for an explicit go before production.\n",
    })
    c = TestClient(create_app(ws))
    r = c.post("/api/promote", json={"id": "ws/memory/prod_gate.md", "path": "guardrails/shared/prod-gate.md",
                                     "text": "# Production gate\n\n- Wait for an explicit go before production.\n",
                                     "area": "deploy", "visibility": "shared", "why": "Make it a team rule"})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "ws/guardrails/shared/prod-gate.md"
    lib = {x["id"]: x for x in c.get("/api/library").json()["entries"]}
    assert lib["ws/memory/prod_gate.md"]["promoted_to"] == "ws/guardrails/shared/prod-gate.md"
    assert lib["ws/memory/prod_gate.md"]["status"] == "deprecated"
    assert lib["ws/guardrails/shared/prod-gate.md"]["confirmed"]
    assert c.post("/api/promote", json={"id": "ws/memory/prod_gate.md", "path": "guardrails/shared/prod-gate.md",
                                        "text": "x", "area": "deploy"}).status_code == 409   # exists
    assert c.post("/api/promote", json={"id": "ws/guardrails/shared/deploy.md", "path": "guardrails/x.md",
                                        "text": "x", "area": "deploy"}).status_code == 409   # not a memory
