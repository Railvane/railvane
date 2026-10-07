"""Split a large guardrail file (e.g. CLAUDE.md) into separate files and skills.

Plan: one part per `##` section (or per `###` when a section is only a container for
sub sections), with a suggestion per part:
  keep    — stays inline
  project — own file in the repository: .claude/guardrails/<name>.md, imported with @
  shared  — reusable: master in the workspace (guardrails/shared/), copy in the repository
  skill   — loaded on demand: .claude/skills/<name>/SKILL.md
Metadata goes to the sidecar manifest, never into the files: agents read frontmatter too.
"""

from __future__ import annotations

import re
import unicodedata

from .classify import guess_area
from .textutil import tokens

HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
PROJECT_MARKERS = re.compile(
    r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"      # IP address
    r"|[A-Za-z]:\\|/home/|/mnt/|%USERPROFILE%"           # machine paths
    r"|\.ps1\b|roadmap item \d+|item \d{2,}"             # project tooling and tickets
    r"|\bport\s*`?\d{2,5}|\bpoort\s*`?\d{2,5}", re.IGNORECASE)


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\(.*?\)", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "section"


def sections(body: str) -> tuple[str, list[dict]]:
    """Split markdown into (preamble, parts). Headings inside code fences are ignored."""
    lines = body.splitlines(keepends=True)
    blocks: list[dict] = []
    current = {"level": 0, "heading": None, "lines": []}
    fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else HEADING.match(line.rstrip("\n"))
        if m:
            blocks.append(current)
            current = {"level": len(m.group(1)), "heading": m.group(2).strip(), "lines": [line]}
        else:
            current["lines"].append(line)
    blocks.append(current)

    preamble = "".join(blocks[0]["lines"])
    parts: list[dict] = []
    i = 1
    while i < len(blocks):
        b = blocks[i]
        children = []
        j = i + 1
        while j < len(blocks) and blocks[j]["level"] > b["level"]:
            children.append(blocks[j])
            j += 1
        own = [ln for ln in b["lines"][1:] if ln.strip()]
        if b["level"] == 2 and children and len(own) <= 1:
            # A container section ("Technical agreements") with sub sections: split those instead
            for c in children:
                parts.append({"heading": c["heading"], "text": "".join(c["lines"]), "parent": b["heading"]})
        else:
            text = "".join(b["lines"]) + "".join("".join(c["lines"]) for c in children)
            parts.append({"heading": b["heading"], "text": text, "parent": None})
        i = j
    for n, p in enumerate(parts):
        p["key"] = f"{n:02d}-{slug(p['heading'])}"
    return preamble, parts


COMMAND = re.compile(r"^\s*(?:\$\s*)?(?:ssh|cd|docker|git|npm|npx|pip|python|export|curl|sudo|kubectl|systemctl)\b"
                     r"|^\s*(?:&|\.\\|\./)", re.IGNORECASE)


def _has_commands(text: str) -> bool:
    """A fenced block whose lines are mostly shell commands (a folder tree or snippet is not)."""
    for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if lines and sum(bool(COMMAND.match(ln)) for ln in lines) >= 0.6 * len(lines):
            return True
    return False


REPO_PATH = re.compile(r"`[\w.${}<>-]+/[\w./${}<>*-]+`")   # a path in this repository, e.g. `frontend/sites/`


def _project_specific(text: str, project: str | None) -> bool:
    if PROJECT_MARKERS.search(text) or REPO_PATH.search(text):
        return True
    return bool(project) and re.search(rf"\b{re.escape(project)}\b", text, re.IGNORECASE) is not None


def suggest(part: dict, project: str | None = None) -> dict:
    text = part["text"]
    body_lines = [ln for ln in text.splitlines()[1:] if ln.strip()]
    refs = sum(1 for ln in body_lines if ln.lstrip().startswith(("@", "- `")))
    if body_lines and refs >= 0.7 * len(body_lines):
        # Only imports or a skills list: this file is already split
        return {"action": "keep", "filename": f"{slug(part['heading'])}.md", "area": None}
    steps = sum(1 for ln in body_lines if re.match(r"\s*\d+\.\s", ln))
    if (_has_commands(text) and len(body_lines) <= 12) or steps >= 6:
        action = "skill"     # a procedure you only need now and then
    elif _project_specific(text, project):
        action = "project"
    else:
        action = "shared"
    area, _, _ = guess_area(slug(part["heading"]), part["heading"], text)
    return {"action": action, "filename": f"{slug(part['heading'])}.md", "area": area}


def plan(body: str, project: str | None = None) -> dict:
    """project: name of the repository (its name in the text marks a part as project specific)."""
    preamble, parts = sections(body)
    return {
        "preamble": preamble,
        "parts": [{**p, "lines": p["text"].count("\n") + 1, "tokens": tokens(p["text"]), "suggestion": suggest(p, project)}
                  for p in parts],
    }


def as_file(part: dict) -> str:
    """A part as a stand-alone file: its heading becomes the title (#)."""
    first, _, rest = part["text"].partition("\n")
    return f"# {part['heading']}\n{rest.rstrip()}\n" if first.startswith("#") else part["text"]


def as_skill(part: dict, name: str) -> str:
    body = as_file(part)
    first = next((ln.strip(" -*") for ln in body.splitlines()[1:] if ln.strip() and not ln.startswith("```")), "")
    description = f"{part['heading']}: {first}"[:300].replace('"', "'")
    return f"---\nname: {name}\ndescription: \"{description}\"\n---\n{body}"
