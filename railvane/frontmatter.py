"""Frontmatter schema v1 for guardrail files.

Required: type, area, visibility, owner.
Optional: tags, status, scope.

Files without frontmatter are not rejected here; they get their metadata from
a sidecar manifest (phase 1).
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .areas import AREA_PHASE

SCHEMA_VERSION = 1

GuardrailType = Literal["project-rules", "memory", "skill", "agent", "index"]
Visibility = Literal["private", "shared"]
Status = Literal["draft", "active", "deprecated"]


class GuardrailMeta(BaseModel):
    # Unknown keys (e.g. name/description used by Claude Code memory) are kept, not rejected
    model_config = ConfigDict(extra="allow")

    type: GuardrailType
    area: str
    visibility: Visibility
    owner: str = Field(min_length=1)
    tags: list[str] = []
    status: Status = "active"
    scope: str | None = None

    @field_validator("area")
    @classmethod
    def area_must_be_known(cls, v: str) -> str:
        if v not in AREA_PHASE:
            raise ValueError(f"unknown area '{v}'")
        return v

    @property
    def phase(self) -> str:
        return AREA_PHASE[self.area]


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split a markdown document into (frontmatter dict, body).

    Returns (None, text) when the document has no frontmatter block.
    Raises ValueError when the block exists but is not a YAML mapping.
    """
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            data = yaml.safe_load("".join(lines[1:i])) or {}
            if not isinstance(data, dict):
                raise ValueError("frontmatter is not a mapping")
            return data, "".join(lines[i + 1:])
    raise ValueError("frontmatter block is not closed")


def validate_meta(data: dict) -> tuple[GuardrailMeta | None, list[str]]:
    """Validate frontmatter data against schema v1. Returns (meta, errors)."""
    try:
        return GuardrailMeta.model_validate(data), []
    except ValidationError as e:
        errors = []
        for err in e.errors():
            field = ".".join(str(p) for p in err["loc"]) or "frontmatter"
            errors.append(f"{field}: {err['msg']}")
        return None, errors


def schema_summary() -> dict:
    """Machine-readable description of the schema, used by the UI."""
    return {
        "version": SCHEMA_VERSION,
        "required": ["type", "area", "visibility", "owner"],
        "optional": ["tags", "status", "scope"],
        "types": list(GuardrailType.__args__),
        "visibility": list(Visibility.__args__),
        "status": list(Status.__args__),
    }
