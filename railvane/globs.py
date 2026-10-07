"""Glob matching on posix relative paths, with ** spanning folders."""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=512)
def _compile(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z", re.IGNORECASE)


def match(path: str, pattern: str) -> bool:
    return _compile(pattern).match(path) is not None


def match_any(path: str, patterns: list[str]) -> bool:
    return any(match(path, p) for p in patterns)


def dir_excluded(rel_dir: str, exclude: list[str]) -> bool:
    """True when nothing below rel_dir can match: used to prune the walk early."""
    probe = rel_dir.rstrip("/") + "/x"
    return any(p.endswith("/**") and match(probe, p) for p in exclude)
