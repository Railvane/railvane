"""Packs: installed (with updates), discover, my packs, publish."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..edit import EditError
from ..gitutil import GitError
from ..packs import manage, publish
from ..packs.overrides import drop_override
from .deps import entry_or_404, index, snapshot, write_guard

router = APIRouter(prefix="/api/packs")


def _root(request) -> Path:
    return Path(snapshot(request).workspace.root)


def _guard(fn):
    try:
        return fn()
    except (manage.PackError, EditError) as e:
        raise HTTPException(409, str(e)) from e


@router.get("")
def installed(request: Request, fetch: bool = False):
    snap = snapshot(request)
    root = Path(snap.workspace.root)
    packs = []
    for ref in snap.workspace.config.packs:
        try:
            info = manage.check_update(root, ref, fetch=fetch)
        except (GitError, OSError, ValueError) as e:
            info = {"name": ref.source, "source": ref.source, "version": ref.version, "error": str(e)}
        info["overrides"] = [e.path for e in snap.list() if e.pack and e.pack["name"] == info["name"] and e.overridden]
        info["sha"] = ref.sha
        packs.append(info)
    return {"packs": packs}


@router.get("/discover")
def discover(request: Request):
    snap = snapshot(request)
    names = {e.pack["name"] for e in snap.list() if e.pack}
    return {"packs": manage.discover(Path(snap.workspace.root), snap.workspace.config.catalog, names)}


@router.get("/mine")
def mine(request: Request):
    snap = snapshot(request)
    return {"packs": publish.my_packs(Path(snap.workspace.root), snap.workspace.config.publish)}


class InstallBody(BaseModel):
    source: str
    path: str | None = None
    version: str | None = None


@router.post("/install")
@write_guard
def install(request: Request, body: InstallBody):
    result = _guard(lambda: manage.install(_root(request), body.source, body.path, body.version))
    index(request).invalidate()
    return result


class NameBody(BaseModel):
    name: str


@router.post("/remove")
@write_guard
def remove(request: Request, body: NameBody):
    result = _guard(lambda: manage.remove(_root(request), body.name))
    index(request).invalidate()
    return result


class UpdateBody(BaseModel):
    name: str
    keep: list[str] = []
    why: str | None = None


@router.post("/update")
@write_guard
def update(request: Request, body: UpdateBody):
    result = _guard(lambda: manage.apply_update(_root(request), body.name, body.keep, body.why))
    index(request).invalidate()
    return result


class DropBody(BaseModel):
    id: str
    why: str | None = None


@router.post("/drop-override")
@write_guard
def drop(request: Request, body: DropBody):
    snap = snapshot(request)
    e = entry_or_404(snap, body.id)
    if not e.pack:
        raise HTTPException(409, "not a pack rule")
    result = _guard(lambda: drop_override(snap, e, body.why))
    index(request).invalidate()
    return result


class PublishBody(BaseModel):
    folder: str
    version: str
    push: bool = True


@router.post("/publish")
@write_guard
def do_publish(request: Request, body: PublishBody):
    result = _guard(lambda: publish.publish(_root(request), body.folder, body.version, body.push))
    index(request).invalidate()
    return result
