"""Split, promote, copies and the read-only switch for sources."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .. import copies, split, splitapply
from ..config import CONFIG_FILE, load_workspace, save_config
from ..promote import promote
from ..repowrite import RepoWriteError, commit_files
from ..wsgit import commit_workspace
from .deps import entry_or_404, index, snapshot, write_guard

router = APIRouter(prefix="/api")


def _source(snap, source_id):
    for s in snap.sources:
        if s.id == source_id:
            return s
    raise HTTPException(404, f"unknown source: {source_id}")


def _guard(fn):
    try:
        return fn()
    except RepoWriteError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/split/plan")
def split_plan(request: Request, id: str):
    snap = snapshot(request)
    e = entry_or_404(snap, id)
    src = _source(snap, e.source) if not e.pack else None
    return {"id": id, "title": e.title, "tokens": e.tokens, "readonly": bool(e.readonly or (src and src.readonly)),
            "is_copy": bool(e.copy_of), **split.plan(e.body, project=src.repo["name"] if src and src.repo else e.source)}


class SplitBody(BaseModel):
    id: str
    choices: dict[str, dict]
    why: str
    mode: str = "commit"


@router.post("/split/apply")
@write_guard
def split_apply(request: Request, body: SplitBody):
    if not body.why.strip():
        raise HTTPException(409, "say why you split this file")
    snap = snapshot(request, force=True)
    e = entry_or_404(snap, body.id)
    result = _guard(lambda: splitapply.apply(snap, e, _source(snap, e.source), body.choices, body.why, body.mode))
    index(request).invalidate()
    return result


class PromoteBody(BaseModel):
    id: str
    path: str
    text: str
    area: str
    visibility: str = "private"
    why: str | None = None


@router.post("/promote")
@write_guard
def do_promote(request: Request, body: PromoteBody):
    snap = snapshot(request, force=True)
    e = entry_or_404(snap, body.id)
    result = _guard(lambda: promote(snap, e, body.path, body.text, body.area, body.visibility, body.why))
    index(request).invalidate()
    return result


@router.get("/copies")
def list_copies(request: Request):
    return {"copies": copies.rows(snapshot(request))}


class SyncBody(BaseModel):
    source: str | None = None
    why: str | None = None
    mode: str = "commit"


@router.post("/copies/sync")
@write_guard
def sync_copies(request: Request, body: SyncBody):
    snap = snapshot(request, force=True)
    results = {}
    for source_id, files in copies.plan_sync(snap, body.source).items():
        src = _source(snap, source_id)
        why = body.why or "Bring copies in line with their masters in the workspace"
        results[source_id] = _guard(lambda: commit_files(src, files, f"Sync {len(files)} shared guardrail(s)", why, body.mode))
    index(request).invalidate()
    return {"synced": results}


class ReadonlyBody(BaseModel):
    id: str
    readonly: bool


@router.post("/sources/readonly")
@write_guard
def set_readonly(request: Request, body: ReadonlyBody):
    """Switch a source between read-only and editable (changes railvane.yaml)."""
    snap = snapshot(request)
    ids = [s.id for s in snap.sources]
    if body.id not in ids:
        raise HTTPException(404, f"unknown source: {body.id}")
    root = Path(snap.workspace.root)
    ws = load_workspace(root)
    if ws.errors:
        raise HTTPException(409, f"{CONFIG_FILE} has errors; fix them first")
    ws.config.sources[ids.index(body.id)].readonly = body.readonly
    file = save_config(root, ws.config)
    state = "read-only" if body.readonly else "editable"
    sha = commit_workspace(root, [file], f"Make source {body.id} {state}", None)
    index(request).invalidate()
    return {"id": body.id, "readonly": body.readonly, "commit": sha}
