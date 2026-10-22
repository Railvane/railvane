"""Admin module (webheaven-kit product contract): health, usage and audit for this instance.

The instance id and link live in a small data directory (RAILVANE_DATA). It never holds content:
guardrails stay in git.
"""

from __future__ import annotations

import os

from webheaven_kit import AdminProvider, InstanceStore

from . import __version__
from .api.history import workspace_timeline
from .index import Index

DEFAULT_FEED = "https://webheaven.nl/api/public/releases/railvane"
DEFAULT_PAGE = "https://github.com/Railvane/railvane/releases"


class RailvaneAdmin(AdminProvider):
    product = "railvane"
    version = __version__
    features = frozenset({"usage", "audit"})   # no accounts yet, so no users section

    def __init__(self, index: Index, server=None):
        self.index, self.server = index, server
        self.releases_feed = os.environ.get("RAILVANE_RELEASES_FEED", DEFAULT_FEED) or None
        self.releases_page = os.environ.get("RAILVANE_RELEASES_PAGE", DEFAULT_PAGE) or None

    def checks(self) -> dict[str, str]:
        checks = {"workspace": (self.server.error if self.server and self.server.error else "ok")}
        try:
            snap = self.index.get()
            checks["config"] = "; ".join(snap.workspace.errors) or "ok"
        except Exception as e:  # the overview must still load when the index fails
            checks["index"] = f"cannot build the index: {e}"
        return checks

    def info(self) -> dict:
        snap = self.index.get()
        return {"workspace": snap.workspace.config.name,
                "storage": "git URL (server mode)" if self.server else "local folder",
                "sources": len(snap.sources)}

    def usage(self) -> dict:
        entries = self.index.get().list()
        metrics = [
            ("guardrails", "Guardrails", len(entries)),
            ("to_classify", "To classify", sum(1 for e in entries if not e.confirmed and not e.pack)),
            ("from_packs", "From packs", sum(1 for e in entries if e.pack)),
            ("memory", "Memory files", sum(1 for e in entries if e.type == "memory")),
            ("tokens", "Tokens (all files)", sum(e.tokens for e in entries)),
        ]
        return {"metrics": [{"key": k, "label": label, "value": v} for k, label, v in metrics], "period": "now"}

    def audit(self, limit: int) -> list[dict]:
        return [{"time": c["date"], "actor": c["author"], "action": "commit", "target": c["repo"], "detail": c["subject"]}
                for c in workspace_timeline(self.index.get(), limit)]


def instance_store() -> InstanceStore:
    return InstanceStore(os.environ.get("RAILVANE_DATA") or None)
