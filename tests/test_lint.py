from fastapi.testclient import TestClient

from railvane.app import create_app
from railvane.cli import main
from railvane.index import build
from railvane.lint import run_lint
from railvane.lint.share import scan
from tests.conftest import make_repo

SHARED = """---
type: memory
area: deploy
visibility: shared
owner: "@bart"
---
# Servers

- Production runs on 192.0.2.10, ask admin@company.nl for access.
- password: hunter2secret
- Localhost 127.0.0.1 is fine.
"""


def rules(findings, eid=None):
    return {f.rule for f in findings if eid is None or f.id == eid}


def test_share_scan():
    found = scan(SHARED)
    msgs = " ".join(m for _, _, m in found)
    assert "192.0.2.10" in msgs and "admin@company.nl" in msgs and "password" in msgs
    assert "127.0.0.1" not in msgs
    assert scan("token ghp_" + "a" * 36)[0][1] == "error"
    assert scan("version 1.2.3 and v10.0.0.1x") == []


def test_rules(workspace):
    (workspace / "memory" / "servers.md").write_text(SHARED, encoding="utf-8")
    (workspace / "memory" / "long.md").write_text("# Long\n" + "line\n" * 320, encoding="utf-8")
    f = run_lint(build(workspace))
    assert {"share-secret", "share-personal"} <= rules(f, "test-ws/memory/servers.md")
    assert "file-too-long" in rules(f, "test-ws/memory/long.md")
    assert "dead-link" in rules(f, "test-ws/CLAUDE.md")
    assert "unconfirmed" in rules(f, "test-ws/CLAUDE.md")
    assert "frontmatter-invalid" not in rules(f)
    secret = next(x for x in f if x.rule == "share-secret")
    assert secret.line == 10  # points into the real file, after frontmatter


def test_private_files_are_not_share_checked(workspace):
    (workspace / "memory" / "servers.md").write_text(SHARED.replace("shared", "private"), encoding="utf-8")
    assert not rules(run_lint(build(workspace)), "test-ws/memory/servers.md") & {"share-secret", "share-personal"}


def test_duplicates_and_ignores(workspace):
    dup = "- Never deploy without an explicit order from the user.\n"
    (workspace / "a.md").write_text("# A\n" + dup, encoding="utf-8")
    (workspace / "b.md").write_text("# B\n" + dup + "<!-- railvane-ignore: duplicate-rule -->\n", encoding="utf-8")
    (workspace / "railvane.yaml").write_text("name: test-ws\ninclude: ['*.md', 'memory/*.md']\n", encoding="utf-8")
    f = run_lint(build(workspace))
    dups = [x for x in f if x.rule == "duplicate-rule"]
    assert [x.id for x in dups] == ["test-ws/a.md"] and "b.md" in dups[0].message
    (workspace / "railvane.yaml").write_text(
        "name: test-ws\ninclude: ['*.md']\nlint:\n  ignore: [duplicate-rule, dead-link]\n", encoding="utf-8")
    assert not rules(run_lint(build(workspace))) & {"duplicate-rule", "dead-link"}


def test_cli_lint(tmp_path, capsys):
    clean = make_repo(tmp_path / "clean", {"CLAUDE.md": "# Rules\n\n- Be kind.\n"})
    assert main(["lint", str(clean)]) == 0
    assert main(["lint", str(clean), "--fail-on", "info"]) == 1   # 'unconfirmed' is info
    bad = make_repo(tmp_path / "bad", {"memory/s.md": SHARED})
    capsys.readouterr()
    assert main(["lint", str(bad), "--format", "github"]) == 1
    out = capsys.readouterr().out
    assert "::error file=memory/s.md,line=10,title=railvane share-secret::" in out


def test_quality_api(workspace):
    body = TestClient(create_app(workspace)).get("/api/quality").json()
    assert body["counts"]["warning"] >= 1
    assert "test-ws/CLAUDE.md" in body["by_file"]
    assert body["config"]["max_lines"] == 300
