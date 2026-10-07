"""Classify: review how files were classified and confirm their metadata; add sources."""


from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from ..areas import AREA_PHASE
from ..config import CONFIG_FILE, Source, load_workspace, save_config
from ..frontmatter import schema_summary
from ..manifest import manifest_path, update_manifest
from ..wsgit import WriteError, commit_workspace
from .deps import index, snapshot, write_guard

router = APIRouter(prefix="/api")


def _suggestion(e) -> str:
    if e.confirmed:
        return "ok"
    if e.type == "index":
        return "index"
    if e.confidence < 0.5:
        return "review"
    return "confirm"


@router.get("/classify")
def review(request: Request):
    snap = snapshot(request)
    rows = []
    for e in sorted(snap.list(), key=lambda x: (x.confirmed, x.confidence)):
        if e.pack or e.promoted_to or e.copy_of:
            continue
        rows.append({"id": e.id, "source": e.source, "path": e.path, "title": e.title,
                     "type": e.type, "area": e.area, "alt_areas": e.alt_areas, "visibility": e.visibility,
                     "owner": e.owner, "tags": e.tags, "confidence": e.confidence, "confirmed": e.confirmed,
                     "meta_source": e.meta_source, "errors": e.errors, "suggestion": _suggestion(e)})
    return {"rows": rows, "sources": [s.summary() for s in snap.sources], "schema": schema_summary()}


class ConfirmItem(BaseModel):
    id: str
    type: str
    area: str
    visibility: str
    owner: str
    tags: list[str] = []

    @field_validator("area")
    @classmethod
    def known_area(cls, v):
        if v not in AREA_PHASE:
            raise ValueError(f"unknown area '{v}'")
        return v


class ConfirmBody(BaseModel):
    items: list[ConfirmItem]
    why: str | None = None


@router.post("/classify/confirm")
@write_guard
def confirm(request: Request, body: ConfirmBody):
    """Store confirmed metadata in the sidecar manifest (source files stay untouched)."""
    snap = snapshot(request)
    unknown = [i.id for i in body.items if i.id not in snap.entries]
    if unknown:
        raise HTTPException(404, f"unknown guardrails: {', '.join(unknown)}")
    root = Path(snap.workspace.root)
    try:
        update_manifest(root, {i.id: i.model_dump(exclude={"id"}) for i in body.items})
    except OSError as e:
        raise WriteError(f"cannot write the manifest: {e}") from e
    n = len(body.items)
    sha = commit_workspace(root, [manifest_path(root)], f"Confirm metadata for {n} guardrail{'s' * (n != 1)}",
                           body.why)
    index(request).invalidate()
    return {"confirmed": n, "commit": sha}


class NewSource(BaseModel):
    path: str | None = None
    git: str | None = None
    branch: str | None = None
    name: str | None = None
    readonly: bool = True   # safe default: never write into a repo you only want to read


@router.post("/sources")
@write_guard
def add_source(request: Request, body: NewSource):
    snap = snapshot(request)
    root = Path(snap.workspace.root)
    ws = load_workspace(root)
    if ws.errors:
        raise HTTPException(409, f"{CONFIG_FILE} has errors; fix them first")
    try:
        src = Source(**body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    config = ws.config
    if not ws.config_found:
        config.sources = []   # the implicit "." source becomes explicit only if the user adds it
    config.sources.append(src)
    try:
        file = save_config(root, config)
    except OSError as e:
        raise WriteError(f"cannot write {CONFIG_FILE}: {e}") from e
    sha = commit_workspace(root, [file], f"Add source {src.git or src.path}", None)
    index(request).invalidate()
    return {"sources": len(config.sources), "commit": sha}
