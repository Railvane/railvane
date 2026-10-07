"""In-memory index of all guardrails in a workspace. Rebuilt from disk/git; never persisted."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from . import classify, gitutil, textutil
from .areas import AREA_PHASE
from .config import Workspace, load_workspace
from .frontmatter import schema_summary, split_frontmatter, validate_meta
from .manifest import read_manifest
from .sources import ResolvedSource, resolve_sources

REQUIRED = ("type", "area", "visibility", "owner")
SCHEMA_KEYS = set(REQUIRED) | {"tags", "status", "scope"}
TTL = 15.0   # after this, the index is refreshed in the background


@dataclass
class Entry:
    id: str
    source: str
    path: str
    title: str
    excerpt: str
    type: str
    area: str | None
    phase: str | None
    visibility: str
    owner: str
    tags: list[str]
    status: str
    scope: str | None
    meta_source: str            # frontmatter | sidecar | inferred
    confirmed: bool
    confidence: float
    alt_areas: list[str]
    errors: list[str]
    lines: int
    tokens: int
    hash: str
    readonly: bool
    updated: str | None = None
    links: list[str] = field(default_factory=list)
    resolved_links: list[str] = field(default_factory=list)
    dead_links: list[str] = field(default_factory=list)
    backlinks: list[str] = field(default_factory=list)
    pack: dict | None = None
    overridden: bool = False
    text: str = ""
    body: str = ""
    abs_path: str = ""

    def summary(self) -> dict:
        d = asdict(self)
        for k in ("text", "body", "abs_path"):
            d.pop(k)
        return d


def _field_ok(key: str, value) -> bool:
    allowed = schema_summary()
    if key == "type":
        return value in allowed["types"]
    if key == "visibility":
        return value in allowed["visibility"]
    if key == "status":
        return value in allowed["status"]
    if key == "area":
        return value in AREA_PHASE
    return value not in (None, "")


def make_entry(source: str, path: str, text: str, manifest: dict, defaults, readonly: bool,
               abs_path: str = "", hint: str = "") -> Entry:
    """hint: folder name of the source root, so 'memory/x.md' is recognised in a memory folder."""
    eid = f"{source}/{path}"
    errors: list[str] = []
    try:
        fm, body = split_frontmatter(text)
    except ValueError as e:
        fm, body, errors = None, text, [str(e)]
    fm = fm or {}
    title = textutil.title_of(path, body, fm)
    # Other tools use frontmatter too (Claude Code memory has e.g. `type: feedback`).
    # Only treat it as Railvane frontmatter when at least two required fields are present.
    schema_fm = {k: v for k, v in fm.items() if k in SCHEMA_KEYS}
    valid_fm = False
    if sum(k in schema_fm for k in REQUIRED) >= 2:
        _, errs = validate_meta(fm)
        valid_fm = not errs
        errors += errs
    schema_fm = {k: v for k, v in schema_fm.items() if _field_ok(k, v)}
    side = manifest.get(eid, {})
    area_guess, confidence, alt = classify.guess_area(path, title, body)
    guessed_type = classify.guess_type(f"{hint}/{path}" if hint else path)
    if guessed_type == "index":
        area_guess, confidence = "docs", max(confidence, 0.8)
    inferred = {"type": guessed_type, "area": area_guess,
                "visibility": defaults.visibility, "owner": defaults.owner or ""}
    meta = {**inferred, **side, **schema_fm}
    confirmed = valid_fm or all(side.get(k) or schema_fm.get(k) for k in REQUIRED)
    area = meta.get("area") if meta.get("area") in AREA_PHASE else None
    tags = meta.get("tags") or []
    return Entry(
        id=eid, source=source, path=path, title=title, excerpt=textutil.summary_of(body, fm),
        type=str(meta["type"]), area=area,
        phase=AREA_PHASE.get(area) if area else None, visibility=str(meta["visibility"]),
        owner=str(meta.get("owner") or ""), tags=[str(t) for t in tags] if isinstance(tags, list) else [str(tags)],
        status=str(meta.get("status") or "active"), scope=meta.get("scope"),
        meta_source="frontmatter" if valid_fm else "sidecar" if side else "inferred",
        confirmed=bool(confirmed), confidence=1.0 if confirmed else confidence, alt_areas=alt,
        errors=errors, lines=text.count("\n") + 1, tokens=textutil.tokens(text), hash=textutil.sha(text),
        readonly=readonly, links=textutil.wikilinks(body) + textutil.md_links(body),
        text=text, body=body, abs_path=abs_path,
    )


@dataclass
class Snapshot:
    workspace: Workspace
    sources: list[ResolvedSource]
    entries: dict[str, Entry]
    built_at: float

    def list(self) -> list[Entry]:
        return list(self.entries.values())


def _link_entries(entries: dict[str, Entry]) -> None:
    keys: dict[str, str] = {}
    for e in entries.values():
        stem = PurePosixPath(e.path).stem
        for k in (stem, textutil.norm_key(e.title)):
            keys.setdefault(textutil.norm_key(k), e.id)
    for e in entries.values():
        for link in e.links:
            target = None
            if link.endswith((".md", ".mdc")):
                p = (PurePosixPath(e.path).parent / link).as_posix()
                cand = f"{e.source}/{PurePosixPath(p)}"
                target = cand if cand in entries else None
            else:
                target = keys.get(textutil.norm_key(link))
            if target and target != e.id:
                e.resolved_links.append(target)
                entries[target].backlinks.append(e.id)
            elif not target:
                e.dead_links.append(link)


def _add_dates(src: ResolvedSource, entries: list[Entry]) -> None:
    """Last commit date per file; file modification time when not in git (or uncommitted)."""
    repo = gitutil.repo_root(src.root)
    if repo:
        rel = {gitutil.rel_to_repo(repo, Path(e.abs_path)): e for e in entries}
        for path, date in gitutil.last_changes(repo, list(rel)).items():
            rel[path].updated = date
    for e in entries:
        if not e.updated:
            mtime = Path(e.abs_path).stat().st_mtime
            e.updated = datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="seconds")


def build(ws_root: Path, fetch: bool = False, extra=None) -> Snapshot:
    ws = load_workspace(ws_root)
    root = Path(ws.root)
    sources = resolve_sources(root, ws.config, fetch=fetch)
    manifest = read_manifest(root)
    entries: dict[str, Entry] = {}
    for src in sources:
        made = []
        for rel in src.files:
            f = src.root / rel
            text = f.read_text(encoding="utf-8", errors="replace")
            e = make_entry(src.id, rel, text, manifest, ws.config.defaults, src.readonly, str(f),
                           hint=src.root.name)
            entries[e.id] = e
            made.append(e)
        if made:
            _add_dates(src, made)
    if extra:  # e.g. installed packs
        for e in extra(ws, manifest):
            entries[e.id] = e
    _link_entries(entries)
    return Snapshot(ws, sources, entries, time.time())


class Index:
    """Cache around build(). Requests never wait for a periodic refresh: a stale snapshot is
    served while a new one is built in the background. Only the first request, an explicit
    fetch and the first request after a change Railvane made itself build inline."""

    def __init__(self, ws_root: str | Path, extra=None, sync=None):
        self.root = Path(ws_root).resolve()
        self.extra = extra
        self.sync = sync   # server mode: pulls the workspace before rebuilding
        self._snap: Snapshot | None = None
        self._lock = threading.Lock()        # guards _snap
        self._build_lock = threading.Lock()  # one build at a time
        self._refreshing = False

    def _rebuild(self, fetch: bool = False) -> Snapshot:
        with self._build_lock:
            if self.sync:
                self.sync(force=fetch)
            snap = build(self.root, fetch=fetch, extra=self.extra)
            with self._lock:
                self._snap = snap
            return snap

    def _refresh_in_background(self) -> None:
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True

        def run():
            try:
                self._rebuild()
            except Exception:  # noqa: BLE001 - keep serving the previous snapshot
                pass
            finally:
                self._refreshing = False
        threading.Thread(target=run, daemon=True).start()

    def get(self, force: bool = False, fetch: bool = False) -> Snapshot:
        with self._lock:
            snap = self._snap
        if snap and not force and not fetch:
            if time.time() - snap.built_at > TTL:
                self._refresh_in_background()
            return snap
        return self._rebuild(fetch=fetch)

    def invalidate(self) -> None:
        with self._lock:
            self._snap = None


def search(entries: list[Entry], query: str) -> list[tuple[Entry, int]]:
    words = [w for w in query.lower().split() if w]
    hits = []
    for e in entries:
        score = 0
        hay_title, hay_path, body = e.title.lower(), e.path.lower(), e.body.lower()
        for w in words:
            s = 5 * (w in hay_title) + 3 * (w in hay_path) + 3 * any(w in t.lower() for t in e.tags)
            s += min(body.count(w), 5)
            if not s:
                break
            score += s
        else:
            if score:
                hits.append((e, score))
    return sorted(hits, key=lambda h: -h[1])
