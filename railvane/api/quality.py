"""Quality: lint findings for the whole workspace."""

from fastapi import APIRouter, Request

from ..lint import run_lint, summarize
from .deps import snapshot

router = APIRouter(prefix="/api")


@router.get("/quality")
def quality(request: Request):
    snap = snapshot(request)
    return {**summarize(run_lint(snap)), "config": snap.workspace.config.lint.model_dump()}
