"""Installed packs as library entries. Pack files are read at their pinned tag;
a local override in .railvane/overrides/<pack>/ replaces the upstream text."""

from __future__ import annotations

from pathlib import Path

from ..config import RAILVANE_DIR, PackRef, Workspace
from ..gitutil import GitError
from ..index import Entry, make_entry
from .store import PackSource, open_pack, slug

OVERRIDES = f"{RAILVANE_DIR}/overrides"


class PackDefaults:
    def __init__(self, owner: str | None):
        self.visibility = "shared"   # a pack is shared by definition
        self.owner = owner


def override_path(ws_root: Path, pack_name: str, rel: str) -> Path:
    return Path(ws_root) / OVERRIDES / slug(pack_name) / rel


def load_ref(ws_root: Path, ref: PackRef) -> tuple[PackSource, str | None]:
    ps = open_pack(ws_root, ref.source, ref.path)
    tag = ps.ref_for(ref.version) if ref.version else None
    return ps, tag or ref.sha


def pack_entries(ws: Workspace, manifest: dict) -> list[Entry]:
    root = Path(ws.root)
    out: list[Entry] = []
    for ref in ws.config.packs:
        try:
            ps, at = load_ref(root, ref)
            meta = ps.meta(at)
            files = ps.files(at)
        except (GitError, OSError, ValueError):
            continue  # shown as an error in the Packs view; the library stays usable
        defaults = PackDefaults(meta.owner or meta.name)
        for rel, upstream in files.items():
            ov = override_path(root, meta.name, rel)
            text = ov.read_text(encoding="utf-8") if ov.exists() else upstream
            e = make_entry(f"pack:{meta.name}", rel, text, manifest, defaults, readonly=False,
                           abs_path=str(ov) if ov.exists() else "")
            e.pack = {"name": meta.name, "version": ref.version, "source": ref.source}
            e.overridden = ov.exists()
            out.append(e)
    return out
