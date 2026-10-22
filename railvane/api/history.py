"""History, timeline, diffs, edits and reverts."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .. import history
from ..edit import EditError, save
from ..gitutil import GitError, git, rel_to_repo, repo_root
from ..wsgit import push_if_enabled
from .deps import entry_or_404, index, snapshot, write_guard

router = APIRouter(prefix="/api")


def _source(snap, source_id):
    for s in snap.sources:
        if s.id == source_id:
            return s
    raise HTTPException(404, f"unknown source: {source_id}")


def _repo_of(entry):
    if not entry.abs_path:
        raise HTTPException(409, "this guardrail has no file history")
    repo = repo_root(Path(entry.abs_path))
    if not repo:
        raise HTTPException(409, "this file is not in a git repository, so it has no history")
    return repo, rel_to_repo(repo, Path(entry.abs_path))


@router.get("/history")
def file_history(request: Request, id: str, limit: int = 50):
    e = entry_or_404(snapshot(request), id)
    repo, rel = _repo_of(e)
    return {"id": id, "commits": history.file_history(repo, rel, limit)}


@router.get("/timeline")
def timeline(request: Request, limit: int = 60):
    """Recent changes to guardrails (and workspace settings) across all repositories."""
    return {"commits": workspace_timeline(snapshot(request), limit)}


def workspace_timeline(snap, limit: int) -> list[dict]:
    """Commits that touched guardrails or workspace settings, newest first (also the admin audit)."""
    by_repo: dict[Path, dict[str, str | None]] = {}
    for e in snap.list():
        if e.abs_path and (repo := repo_root(Path(e.abs_path))):
            by_repo.setdefault(repo, {})[rel_to_repo(repo, Path(e.abs_path))] = e.id
    ws_root = Path(snap.workspace.root)
    if ws_repo := repo_root(ws_root):
        for name in ("railvane.yaml", ".railvane/manifest.yaml"):
            if (ws_root / name).exists():
                by_repo.setdefault(ws_repo, {})[rel_to_repo(ws_repo, ws_root / name)] = None
    commits = []
    for repo, files in by_repo.items():
        for c in history.repo_log(repo, list(files), limit):
            c["repo"] = repo.name
            c["ids"] = [files[f] for f in c["files"] if files.get(f)]
            c["settings"] = [f for f in c["files"] if f in files and files[f] is None]
            commits.append(c)
    # Parse the dates: as text, commits with different UTC offsets sort wrongly
    commits.sort(key=lambda c: datetime.fromisoformat(c["date"]), reverse=True)
    return commits[:limit]


@router.get("/diff")
def diff(request: Request, id: str, sha: str):
    e = entry_or_404(snapshot(request), id)
    repo, rel = _repo_of(e)
    return {"id": id, "sha": sha, "diff": history.show_diff(repo, sha, rel)}


@router.get("/file-at")
def file_at(request: Request, id: str, sha: str):
    e = entry_or_404(snapshot(request), id)
    repo, rel = _repo_of(e)
    return {"id": id, "sha": sha, "text": history.file_at(repo, sha, rel)}


class EditBody(BaseModel):
    id: str
    text: str
    base_hash: str
    why: str
    mode: str = "commit"
    subject: str | None = None


@router.put("/file")
@write_guard
def edit_file(request: Request, body: EditBody):
    snap = snapshot(request, force=True)
    e = entry_or_404(snap, body.id)
    try:
        if e.pack:  # pack files are never edited upstream: the change becomes a local override
            from ..packs.overrides import save_override
            result = save_override(snap, e, body.text, body.base_hash, body.why)
        else:
            result = save(e, _source(snap, e.source), body.text, body.base_hash, body.why, body.mode, body.subject)
    except EditError as err:
        raise HTTPException(409, str(err)) from err
    index(request).invalidate()
    return result


class RevertBody(BaseModel):
    id: str
    sha: str
    why: str


@router.post("/revert")
@write_guard
def revert(request: Request, body: RevertBody):
    snap = snapshot(request)
    e = entry_or_404(snap, body.id)
    if e.readonly or e.pack:
        raise HTTPException(409, "this source is read-only")
    if not body.why.strip():
        raise HTTPException(409, "say why you revert this change")
    repo, _ = _repo_of(e)
    sha = history.revert(repo, body.sha, body.why)
    if _source(snap, e.source).kind == "path":
        push_if_enabled(repo)   # server mode
    else:  # Railvane's clone: publish the revert
        try:
            git(["push", "-q", "origin", "HEAD"], cwd=repo, network=True)
        except GitError as err:
            git(["reset", "-q", "--hard", "HEAD~1"], cwd=repo)
            raise HTTPException(409, f"push failed, nothing changed: {err}") from err
    index(request).invalidate()
    return {"commit": sha}
