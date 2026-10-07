"""Library: list, read and search guardrails."""


from fastapi import APIRouter, Request

from ..index import search
from .deps import entry_or_404, facets, index, snapshot

router = APIRouter(prefix="/api")


@router.get("/library")
def library(request: Request):
    snap = snapshot(request)
    entries = snap.list()
    return {
        "workspace": snap.workspace.config.name,
        "sources": [s.summary() for s in snap.sources],
        "entries": [e.summary() for e in entries],
        "facets": facets(entries),
        "built_at": snap.built_at,
    }


@router.get("/file")
def read_file(request: Request, id: str):
    e = entry_or_404(snapshot(request), id)
    return {**e.summary(), "text": e.text, "body": e.body}


@router.get("/search")
def do_search(request: Request, q: str, limit: int = 50):
    hits = search(snapshot(request).list(), q)[:limit]
    return {"query": q, "results": [{"id": e.id, "score": s} for e, s in hits]}


@router.post("/refresh")
def refresh(request: Request):
    """Fetch git sources and rebuild the index."""
    snap = index(request).get(fetch=True)
    return {"entries": len(snap.entries), "sources": [s.summary() for s in snap.sources]}
