"""Library: list, read and search guardrails."""


from fastapi import APIRouter, Request

from ..gitutil import display_path, repo_info
from ..index import search
from .deps import entry_or_404, facets, index, snapshot

router = APIRouter(prefix="/api")


@router.get("/library")
def library(request: Request):
    snap = snapshot(request)
    entries = snap.list()
    return {
        "workspace": snap.workspace.config.name,
        "workspace_repo": repo_info(snap.workspace.root),
        "workspace_root": display_path(snap.workspace.root),
        "sources": [s.summary() for s in snap.sources],
        "entries": [e.summary() for e in entries],
        "facets": facets(entries),
        "built_at": snap.built_at,
        "server": request.app.state.server.summary() if request.app.state.server else None,
    }


@router.get("/file")
def read_file(request: Request, id: str):
    snap = snapshot(request)
    e = entry_or_404(snap, id)
    kind = next((s.kind for s in snap.sources if s.id == e.source), "pack" if e.pack else None)
    return {**e.summary(), "text": e.text, "body": e.body, "source_kind": kind}


@router.get("/search")
def do_search(request: Request, q: str, limit: int = 50):
    hits = search(snapshot(request).list(), q)[:limit]
    return {"query": q, "results": [{"id": e.id, "score": s} for e, s in hits]}


@router.post("/refresh")
def refresh(request: Request):
    """Fetch git sources and rebuild the index."""
    snap = index(request).get(fetch=True)
    return {"entries": len(snap.entries), "sources": [s.summary() for s in snap.sources]}
