import pytest

from railvane.frontmatter import schema_summary, split_frontmatter, validate_meta

VALID = """---
type: memory
area: deploy
visibility: shared
owner: "@bart"
tags: [deploy]
---
# Never deploy without an explicit order
"""


def test_split_returns_data_and_body():
    data, body = split_frontmatter(VALID)
    assert data["area"] == "deploy"
    assert body.startswith("# Never deploy")


def test_split_without_frontmatter():
    data, body = split_frontmatter("# Just markdown\n")
    assert data is None
    assert body == "# Just markdown\n"


def test_split_handles_bom():
    data, _ = split_frontmatter("﻿" + VALID)
    assert data["type"] == "memory"


def test_split_unclosed_block_raises():
    with pytest.raises(ValueError, match="not closed"):
        split_frontmatter("---\ntype: memory\n# no closing line\n")


def test_split_non_mapping_raises():
    with pytest.raises(ValueError, match="mapping"):
        split_frontmatter("---\n- a\n- b\n---\nbody\n")


def test_valid_meta():
    data, _ = split_frontmatter(VALID)
    meta, errors = validate_meta(data)
    assert errors == []
    assert meta.phase == "release"
    assert meta.status == "active"


def test_missing_required_fields():
    meta, errors = validate_meta({"type": "memory"})
    assert meta is None
    assert {e.split(":")[0] for e in errors} == {"area", "visibility", "owner"}


def test_unknown_area_and_visibility():
    _, errors = validate_meta({"type": "memory", "area": "nope", "visibility": "public", "owner": "x"})
    assert any(e.startswith("area:") and "unknown area" in e for e in errors)
    assert any(e.startswith("visibility:") for e in errors)


def test_extra_keys_are_kept():
    meta, errors = validate_meta({"type": "memory", "area": "git", "visibility": "private",
                                  "owner": "x", "name": "branching", "description": "d"})
    assert errors == []
    assert meta.model_extra["name"] == "branching"


def test_schema_summary():
    s = schema_summary()
    assert s["required"] == ["type", "area", "visibility", "owner"]
    assert "shared" in s["visibility"]
