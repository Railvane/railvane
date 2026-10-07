"""Workspace configuration: railvane.yaml in the workspace root.

There is no database. Everything Railvane knows lives in git: this file,
the markdown files themselves and (later) sidecar manifests.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

CONFIG_FILE = "railvane.yaml"

DEFAULT_INCLUDE = [
    "**/CLAUDE.md", "**/AGENTS.md", "**/.cursorrules", "**/.cursor/rules/*.mdc",
    "**/.claude/**/*.md", "**/memory/*.md",
]
DEFAULT_EXCLUDE = ["**/node_modules/**", "**/.git/**", "**/.venv/**"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = None
    git: str | None = None
    branch: str | None = None
    include: list[str] | None = None
    exclude: list[str] | None = None

    @model_validator(mode="after")
    def exactly_one_location(self) -> "Source":
        if bool(self.path) == bool(self.git):
            raise ValueError("a source needs exactly one of 'path' or 'git'")
        if self.branch and not self.git:
            raise ValueError("'branch' only applies to git sources")
        return self


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visibility: str = "private"
    owner: str | None = None


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    name: str = "workspace"
    sources: list[Source] = [Source(path=".")]
    include: list[str] = DEFAULT_INCLUDE
    exclude: list[str] = DEFAULT_EXCLUDE
    defaults: Defaults = Defaults()
    packs: list[str] = []

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
