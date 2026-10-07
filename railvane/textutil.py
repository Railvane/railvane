"""Small text helpers for markdown guardrails."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
MDLINK = re.compile(r"\]\(([^)\s]+?\.mdc?)(?:#[^)]*)?\)")
HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)


def norm_key(text: str) -> str:
    return re.sub(r"[\s_]+", "-", text.strip().lower())


def title_of(rel_path: str, body: str, fm: dict | None) -> str:
    """Explicit title, else the first heading, else the frontmatter name, else the file name."""
    fm = fm or {}
    if isinstance(fm.get("title"), str) and fm["title"].strip():
        return fm["title"].strip()
    m = HEADING.search(body)
    if m:
        return m.group(1).strip()
    if isinstance(fm.get("name"), str) and fm["name"].strip():
        return fm["name"].strip()
    return PurePosixPath(rel_path).name


def summary_of(body: str, fm: dict | None, limit: int = 180) -> str:
    """Frontmatter description, else the first paragraph that is not a heading."""
    fm = fm or {}
    if isinstance(fm.get("description"), str) and fm["description"].strip():
        text = fm["description"].strip()
    else:
        text = ""
        for block in re.split(r"\n\s*\n", body):
            block = block.strip()
            if block and not block.startswith(("#", "```", "|", "<")):
                text = re.sub(r"\s+", " ", block)
                break
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def tokens(text: str) -> int:
    """Rough token estimate (about 4 characters per token)."""
    return max(1, round(len(text) / 4))


def wikilinks(body: str) -> list[str]:
    return sorted({m.group(1).strip() for m in WIKILINK.finditer(body)})


def md_links(body: str) -> list[str]:
    return sorted({m.group(1) for m in MDLINK.finditer(body) if "://" not in m.group(1)})


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
