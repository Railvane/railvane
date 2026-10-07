"""Rule-based classification: guess type and lifecycle area of a guardrail file.

No AI here: path rules for the type, keyword scoring for the area. The result
carries a confidence so the UI can ask the user to confirm low-confidence guesses.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

KEYWORDS: dict[str, list[str]] = {
    "ideation": ["idea", "idee", "intake", "brainstorm"],
    "requirements": ["requirement", "user story", "persona", "acceptance criteria"],
    "priority": ["roadmap", "backlog", "prioriti", "priority"],
    "architecture": ["architect", "adr", "design decision", "project structure", "projectstructuur", "monorepo"],
    "ux": ["ux", "ui", "css", "layout", "design token", "button", "knop", "mockup", "flexbox", "screen"],
    "data": ["database", "alembic", "migration", "migratie", "sqlite", "table", "tabel", "column", "kolom"],
    "api": ["endpoint", "rest api", "api", "router", "http"],
    "coding": ["naming", "naamgeving", "code style", "comments", "variable", "300 lines", "300 regels", "file size"],
    "stack": ["python", "fastapi", "react", "vite", "powershell", "node", "npm", "venv", "pip"],
    "git": ["git", "branch", "merge", "cherry-pick", "commit", "rebase", "pull request"],
    "review": ["code review", "review", "checklist"],
    "deps": ["dependency", "dependencies", "package", "license", "licentie"],
    "ai": ["claude", "agent", "llm", "prompt", "ai", "mindbox"],
    "testing": ["test", "pytest", "eslint", "lint", "regression"],
    "security": ["secret", "token", "password", "wachtwoord", "ssh", "auth", "permission"],
    "privacy": ["privacy", "gdpr", "avg", "personal data", "persoonsgegevens"],
    "i18n": ["i18n", "translation", "vertaling", "language", "taal", "locale"],
    "cicd": ["github actions", "ci", "pipeline", "workflow", "ghcr", "docker build"],
    "versioning": ["version", "versie", "changelog", "release", "semver"],
    "deploy": ["deploy", "production", "productie", "acceptance", "acceptatie", "prod", "server", "cutover"],
    "config": ["env", "environment", "configuration", "config", "compose"],
    "monitoring": ["sentry", "glitchtip", "monitoring", "logging", "alert", "bugsink"],
    "incident": ["incident", "outage", "storing", "runbook", "escalat", "post-mortem"],
    "backup": ["backup", "restore", "snapshot", "herstel"],
    "maintenance": ["cleanup", "opruimen", "tech debt", "deprecat", "refactor"],
    "docs": ["readme", "documentation", "documentatie", "onboarding"],
}


def _pattern(word: str) -> re.Pattern:
    # Short words must match as whole words ("ui" must not match "build")
    if len(word) <= 4 and " " not in word:
        return re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    return re.compile(re.escape(word), re.IGNORECASE)


_COMPILED = {area: [_pattern(w) for w in words] for area, words in KEYWORDS.items()}


def guess_type(rel_path: str) -> str:
    p = PurePosixPath(rel_path.lower())
    parts = p.parts
    if p.name == "memory.md":
        return "index"
    if "memory" in parts[:-1]:
        return "memory"
    if ".claude" in parts and "skills" in parts or ".claude" in parts and "commands" in parts:
        return "skill"
    if ".claude" in parts and "agents" in parts:
        return "agent"
    return "project-rules"


def guess_area(rel_path: str, title: str, body: str) -> tuple[str | None, float, list[str]]:
    """Return (area, confidence 0..1, runner-up areas)."""
    name = PurePosixPath(rel_path).stem.replace("_", " ").replace("-", " ")
    body = body[:20000]
    scores: dict[str, float] = {}
    for area, patterns in _COMPILED.items():
        s = 0.0
        for pat in patterns:
            s += 4 * len(pat.findall(name)) + 2 * len(pat.findall(title)) + min(len(pat.findall(body)), 6)
        if s:
            scores[area] = s
    if not scores:
        return None, 0.0, []
    ranked = sorted(scores, key=scores.get, reverse=True)
    top = scores[ranked[0]]
    second = scores[ranked[1]] if len(ranked) > 1 else 0.0
    confidence = round(min(1.0, (top - second) / top * 0.7 + min(top, 12) / 12 * 0.3), 2)
    return ranked[0], confidence, ranked[1:3]
