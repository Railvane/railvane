"""Workspace configuration: railvane.yaml in the workspace root.

There is no database. Everything Railvane knows lives in git: this file,
the markdown files themselves and the sidecar manifest in .railvane/.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

CONFIG_FILE = "railvane.yaml"
RAILVANE_DIR = ".railvane"

DEFAULT_INCLUDE = [
    "**/CLAUDE.md", "**/AGENTS.md", "**/.cursorrules", "**/.cursor/rules/*.mdc",
    "**/.claude/**/*.md", "**/memory/*.md", "**/.github/copilot-instructions.md",
]
DEFAULT_EXCLUDE = [
    "**/node_modules/**", "**/.git/**", "**/.venv/**", "**/.railvane/**", "**/dist/**",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(_Strict):
    path: str | None = None
    git: str | None = None
    branch: str | None = None
    name: str | None = None
    readonly: bool = False
    include: list[str] | None = None
    exclude: list[str] | None = None

    @model_validator(mode="after")
    def exactly_one_location(self) -> "Source":
        if bool(self.path) == bool(self.git):
            raise ValueError("a source needs exactly one of 'path' or 'git'")
        if self.branch and not self.git:
            raise ValueError("'branch' only applies to git sources")
        return self


class Defaults(_Strict):
    visibility: str = "private"
    owner: str | None = None


class LintConfig(_Strict):
    max_lines: int = 300
    max_tokens: int = 2000
    stale_days: int = 180
    ignore: list[str] = []


class PackRef(_Strict):
    """An installed pack, pinned to a version and commit."""
    source: str                 # git URL or path (relative to the workspace)
    path: str | None = None     # sub folder inside the source, if any
    version: str | None = None
    sha: str | None = None


class WorkspaceConfig(_Strict):
    version: int = 1
    name: str = "workspace"
    sources: list[Source] = [Source(path=".")]
    include: list[str] = DEFAULT_INCLUDE
    exclude: list[str] = DEFAULT_EXCLUDE
    defaults: Defaults = Defaults()
    lint: LintConfig = LintConfig()
    packs: list[PackRef] = []
    catalog: list[str] = []     # pack sources offered under "Discover"
    publish: list[str] = []     # folders in this workspace that are packs you publish

    @model_validator(mode="after")
    def supported_version(self) -> "WorkspaceConfig":
        if self.version != 1:
            raise ValueError(f"unsupported config version {self.version}")
        return self


class Workspace(BaseModel):
    root: str
    config_found: bool
    config: WorkspaceConfig
    errors: list[str] = []


def load_workspace(root: str | Path) -> Workspace:
    """Load railvane.yaml from root. A missing file gives sensible defaults;
    an invalid file gives defaults plus the errors, so the UI can show them."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"workspace folder not found: {root}")
    file = root / CONFIG_FILE
    if not file.exists():
        return Workspace(root=str(root), config_found=False,
                         config=WorkspaceConfig(name=root.name))
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{CONFIG_FILE} must be a mapping")
        return Workspace(root=str(root), config_found=True,
                         config=WorkspaceConfig.model_validate(data))
    except (ValueError, yaml.YAMLError) as e:
        errors = ([f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()]
                  if isinstance(e, ValidationError) else [str(e)])
        return Workspace(root=str(root), config_found=True,
                         config=WorkspaceConfig(name=root.name), errors=errors)


HEADER = "# railvane.yaml — Railvane workspace configuration (schema version 1)\n" \
         "# Railvane rewrites this file when you change settings in the UI; comments are not kept.\n"


def save_config(root: str | Path, config: WorkspaceConfig) -> Path:
    """Write railvane.yaml. Only non-default values are written, to keep the file short."""
    data = config.model_dump(exclude_defaults=True)
    data = {"version": 1, "name": config.name, **data}
    file = Path(root) / CONFIG_FILE
    file.write_text(HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return file
