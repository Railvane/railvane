import pytest

from railvane.config import load_workspace


def write(tmp_path, text):
    (tmp_path / "railvane.yaml").write_text(text, encoding="utf-8")


def test_missing_config_gives_defaults(tmp_path):
    ws = load_workspace(tmp_path)
    assert ws.config_found is False
    assert ws.errors == []
    assert ws.config.name == tmp_path.name
    assert ws.config.sources[0].path == "."


def test_valid_config(tmp_path):
    write(tmp_path, """
version: 1
name: bart-guardrails
sources:
  - path: .
  - git: https://github.com/example/rules.git
    branch: main
defaults:
  visibility: shared
  owner: "@bart"
""")
    ws = load_workspace(tmp_path)
    assert ws.errors == []
    assert ws.config.name == "bart-guardrails"
    assert ws.config.sources[1].branch == "main"
    assert ws.config.defaults.owner == "@bart"


@pytest.mark.parametrize("source, msg", [
    ("{}", "exactly one"),
    ("{path: ., git: https://x}", "exactly one"),
    ("{path: ., branch: main}", "only applies to git"),
])
def test_invalid_sources(tmp_path, source, msg):
    write(tmp_path, f"sources:\n  - {source}\n")
    ws = load_workspace(tmp_path)
    assert any(msg in e for e in ws.errors)
    assert ws.config.name == tmp_path.name  # falls back to defaults


def test_unknown_key_is_an_error(tmp_path):
    write(tmp_path, "nmae: typo\n")
    assert any("nmae" in e for e in load_workspace(tmp_path).errors)


def test_unsupported_version(tmp_path):
    write(tmp_path, "version: 2\n")
    assert any("unsupported config version" in e for e in load_workspace(tmp_path).errors)


def test_broken_yaml(tmp_path):
    write(tmp_path, "sources: [\n")
    assert load_workspace(tmp_path).errors


def test_missing_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_workspace(tmp_path / "nope")
