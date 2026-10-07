"""Shared helpers for the routers."""

from __future__ import annotations

import functools
from collections import Counter

from fastapi import HTTPException, Request

from ..index import Entry, Index, Snapshot
from ..gitutil import GitError
from ..wsgit import WriteError


def index(request: Request) -> Index:
    return request.app.state.index


def snapshot(request: Request, force: bool = False) -> Snapshot:
    return index(request).get(force=force)


def entry_or_404(snap: Snapshot, eid: str) -> Entry:
    e = snap.entries.get(eid)
    if not e:
        raise HTTPException(404, f"unknown guardrail: {eid}")
    return e


def facets(entries: list[Entry]) -> dict:
    return {
        "type": Counter(e.type for e in entries),
        "area": Counter(e.area or "none" for e in entries),
        "phase": Counter(e.phase or "none" for e in entries),
        "visibility": Counter(e.visibility for e in entries),
        "source": Counter(e.source for e in entries),
        "tags": Counter(t for e in entries for t in e.tags),
    }


def write_guard(fn):
    """Turn write and git problems into a clean 409 instead of a 500."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (WriteError, GitError) as e:
            raise HTTPException(409, str(e)) from e
    return wrapper
