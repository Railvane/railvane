"""Output formats for `railvane lint`."""

from __future__ import annotations

import json

from .runner import SEVERITY, Finding

ICON = {"error": "✕", "warning": "⚠", "info": "·"}
GITHUB_LEVEL = {"error": "error", "warning": "warning", "info": "notice"}


def text(findings: list[Finding], paths: dict[str, str]) -> str:
    if not findings:
        return "✓ No findings."
    lines = []
    for x in findings:
        where = paths.get(x.id, x.id) + (f":{x.line}" if x.line else "")
        lines.append(f"{ICON[x.severity]} {where}  {x.message}  [{x.rule}]")
    counts = {s: sum(x.severity == s for x in findings) for s in SEVERITY}
    lines.append(f"\n{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info")
    return "\n".join(lines)


def as_json(findings: list[Finding]) -> str:
    return json.dumps([x.dict() for x in findings], indent=2)


def github(findings: list[Finding], paths: dict[str, str]) -> str:
    """GitHub Actions workflow commands: findings show up as annotations on the PR."""
    out = []
    for x in findings:
        loc = f"file={paths.get(x.id, x.id)}" + (f",line={x.line}" if x.line else "")
        msg = x.message.replace("%", "%25").replace("\n", "%0A")
        out.append(f"::{GITHUB_LEVEL[x.severity]} {loc},title=railvane {x.rule}::{msg}")
    return "\n".join(out)


def fails(findings: list[Finding], fail_on: str) -> bool:
    if fail_on == "never":
        return False
    return any(SEVERITY[x.severity] >= SEVERITY[fail_on] for x in findings)
