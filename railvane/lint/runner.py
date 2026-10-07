"""Lint rules. Each finding names a rule id that can be ignored in railvane.yaml
(lint.ignore) or per file with <!-- railvane-ignore: rule-id -->."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from ..config import LintConfig
from . import share

SEVERITY = {"error": 3, "warning": 2, "info": 1}
IGNORE = re.compile(r"<!--\s*railvane-ignore:\s*([\w\s,-]+?)\s*-->")
RULE_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


@dataclass
class Finding:
    rule: str
    severity: str
    id: str
    message: str
    line: int | None = None

    def dict(self) -> dict:
        return asdict(self)


def _norm(text: str) -> str:
    text = re.sub(r"[`*_\[\]()>#]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip(" .;:!")


def _rule_lines(body: str) -> list[tuple[int, str]]:
    out = []
    for n, line in enumerate(body.splitlines(), start=1):
        m = RULE_LINE.match(line)
        if m and len(_norm(m.group(1))) >= 25:
            out.append((n, _norm(m.group(1))))
    return out


def _body_offset(entry) -> int:
    """Lines before the body (frontmatter), so line numbers point into the real file."""
    return entry.text.count("\n") - entry.body.count("\n")


def _per_entry(e, cfg: LintConfig, now: datetime) -> list[Finding]:
    f: list[Finding] = []
    for err in e.errors:
        f.append(Finding("frontmatter-invalid", "error", e.id, err, 1))
    if not e.confirmed and not e.errors and e.type != "index":
        f.append(Finding("unconfirmed", "info", e.id, "metadata is guessed; confirm it in Import"))
    if e.lines > cfg.max_lines:
        f.append(Finding("file-too-long", "warning", e.id, f"{e.lines} lines (limit {cfg.max_lines}); consider splitting"))
    if e.tokens > cfg.max_tokens:
        f.append(Finding("token-heavy", "warning", e.id, f"~{e.tokens} tokens (budget {cfg.max_tokens}); agents follow lean rules better"))
    for link in e.dead_links:
        f.append(Finding("dead-link", "warning", e.id, f"link to '{link}' does not resolve"))
    if e.updated and e.status != "deprecated":
        age = (now - datetime.fromisoformat(e.updated)).days
        if age > cfg.stale_days:
            f.append(Finding("stale", "info", e.id, f"not changed in {age} days; still relevant?"))
    if e.visibility == "shared" or e.pack:
        for line, sev, msg in share.scan(e.text):
            f.append(Finding("share-secret" if sev == "error" else "share-personal", sev, e.id,
                             f"shared file contains {msg}", line))
    return f


def _duplicates(entries) -> list[Finding]:
    seen: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for e in entries:
        if e.type == "index":
            continue
        offset = _body_offset(e)
        for n, text in _rule_lines(e.body):
            seen[text].append((e.id, n + offset))
    out = []
    for text, places in seen.items():
        ids = sorted({i for i, _ in places})
        if len(ids) < 2:
            continue
        for eid, line in places:
            others = ", ".join(i for i in ids if i != eid)
            out.append(Finding("duplicate-rule", "warning", eid, f"same rule also in {others}", line))
    return out


def run_lint(snapshot) -> list[Finding]:
    cfg = snapshot.workspace.config.lint
    now = datetime.now(timezone.utc)
    entries = snapshot.list()
    findings = [x for e in entries for x in _per_entry(e, cfg, now)] + _duplicates(entries)
    ignored_in_file = {e.id: {r.strip() for m in IGNORE.finditer(e.text) for r in m.group(1).split(",")}
                       for e in entries}
    findings = [x for x in findings if x.rule not in cfg.ignore and x.rule not in ignored_in_file.get(x.id, ())]
    return sorted(findings, key=lambda x: (-SEVERITY[x.severity], x.id, x.line or 0))


def summarize(findings: list[Finding]) -> dict:
    counts = {"error": 0, "warning": 0, "info": 0}
    by_file: dict[str, dict] = {}
    for x in findings:
        counts[x.severity] += 1
        f = by_file.setdefault(x.id, {"error": 0, "warning": 0, "info": 0, "items": []})
        f[x.severity] += 1
        f["items"].append(x.dict())
    return {"counts": counts, "by_file": by_file, "findings": [x.dict() for x in findings]}
