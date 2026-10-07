from railvane import globs
from railvane.classify import guess_area, guess_type
from railvane.index import build, search
from railvane.manifest import read_manifest, update_manifest


def test_globs():
    assert globs.match("CLAUDE.md", "**/CLAUDE.md")
    assert globs.match("a/b/CLAUDE.md", "**/CLAUDE.md")
    assert globs.match(".claude/skills/x/SKILL.md", "**/.claude/**/*.md")
    assert not globs.match("memory/sub/x.md", "**/memory/*.md")
    assert globs.dir_excluded("web/node_modules", ["**/node_modules/**"])


def test_guess_type():
    assert guess_type("memory/MEMORY.md") == "index"
    assert guess_type("memory/feedback_x.md") == "memory"
    assert guess_type(".claude/skills/review/SKILL.md") == "skill"
    assert guess_type(".claude/agents/planner.md") == "agent"
    assert guess_type("CLAUDE.md") == "project-rules"


def test_guess_area_prefers_file_name():
    area, conf, _ = guess_area("feedback_alembic_race.md", "", "New migrations need has-table checks.")
    assert area == "data" and conf > 0.5
    assert guess_area("x.md", "", "nothing relevant here")[0] is None


def test_build(workspace):
    snap = build(workspace)
    e = snap.entries
    assert set(e) == {"test-ws/memory/feedback_deploy.md", "test-ws/memory/branching.md", "test-ws/CLAUDE.md"}

    deploy = e["test-ws/memory/feedback_deploy.md"]
    assert deploy.meta_source == "frontmatter" and deploy.confirmed
    assert deploy.phase == "release" and deploy.visibility == "shared"
    assert deploy.updated  # from git

    branching = e["test-ws/memory/branching.md"]
    assert branching.type == "memory"            # foreign `metadata.type` is ignored
    assert not branching.confirmed and branching.errors == []
    assert branching.excerpt == "Always develop to main."
    assert deploy.resolved_links == ["test-ws/memory/branching.md"]
    assert branching.backlinks == ["test-ws/memory/feedback_deploy.md"]

    claude = e["test-ws/CLAUDE.md"]
    assert claude.title == "Project rules" and claude.dead_links == ["missing-note"]
    assert claude.owner == "@bart"               # from config defaults


def test_sidecar_confirms(workspace):
    update_manifest(workspace, {"test-ws/CLAUDE.md": {"type": "project-rules", "area": "coding",
                                                       "visibility": "private", "owner": "@bart"}})
    assert "test-ws/CLAUDE.md" in read_manifest(workspace)
    claude = build(workspace).entries["test-ws/CLAUDE.md"]
    assert claude.confirmed and claude.meta_source == "sidecar" and claude.area == "coding"


def test_invalid_frontmatter_is_reported(workspace):
    (workspace / "memory" / "bad.md").write_text("---\ntype: memory\narea: nope\n---\nx\n", encoding="utf-8")
    bad = build(workspace).entries["test-ws/memory/bad.md"]
    assert any("area" in err for err in bad.errors) and not bad.confirmed


def test_search(workspace):
    hits = search(build(workspace).list(), "deploy order")
    assert hits[0][0].path == "memory/feedback_deploy.md"


def test_readonly_and_missing_source(tmp_path, workspace):
    (workspace / "railvane.yaml").write_text(
        "sources:\n  - path: .\n    readonly: true\n  - path: ../nope\n", encoding="utf-8")
    snap = build(workspace)
    assert all(e.readonly for e in snap.list())
    assert snap.sources[1].error and "not found" in snap.sources[1].error
