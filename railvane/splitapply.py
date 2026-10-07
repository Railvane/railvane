"""Apply a split plan: write the new files, rewrite the original as imports, register copies,
store metadata in the sidecar — all as commits with a why."""

from __future__ import annotations

import os
from pathlib import Path

from .config import Copy, load_workspace, save_config
from .copies import entry_id_for, register, same_text
from .frontmatter import split_frontmatter
from .manifest import manifest_path, update_manifest
from .repowrite import RepoWriteError, commit_files
from .split import as_file, as_skill, sections, slug
from .wsgit import commit_workspace, write_text

ACTIONS = ("keep", "project", "shared", "skill")


def _rel(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target, start)).as_posix()


def apply(snap, entry, src, choices: dict[str, dict], why: str, mode: str = "commit") -> dict:
    if entry.copy_of or entry.pack:
        raise RepoWriteError("split the master file, not a copy or a pack rule")
    file = Path(entry.abs_path)
    ws_root = Path(snap.workspace.root)
    same_repo = file.resolve().is_relative_to(ws_root)
    fm_text = entry.text[: len(entry.text) - len(entry.body)] if split_frontmatter(entry.text)[0] else ""
    preamble, parts = sections(entry.body)

    src_files: dict[Path, str] = {}      # written in the source repository
    ws_files: dict[Path, str] = {}       # masters written in the workspace
    copies: list[Copy] = []
    meta: dict[str, dict] = {}
    out, skills, last_parent, in_imports = [preamble.rstrip() + "\n"], [], None, False
    base_meta = {"visibility": entry.visibility, "owner": entry.owner}

    for part in parts:
        ch = choices.get(part["key"], {"action": "keep"})
        action = ch.get("action", "keep")
        if action not in ACTIONS:
            raise RepoWriteError(f"unknown action {action}")
        name = slug(Path(ch.get("filename") or part["heading"]).stem)
        area = ch.get("area")
        if part["parent"] and part["parent"] != last_parent and action != "skill":
            out.append(f"\n## {part['parent']}\n")
            in_imports = False
        last_parent = part["parent"]
        if action == "keep":
            out.append("\n" + part["text"].strip() + "\n")
            in_imports = False
            continue
        if action == "skill":
            path = file.parent / ".claude" / "skills" / name / "SKILL.md"
            src_files[path] = as_skill(part, name)
            skills.append((name, part["heading"]))
            meta[entry_id_for(snap.sources, path) or str(path)] = {"type": "skill", "area": area, **base_meta}
            continue
        text = as_file(part)
        if action == "project":
            path = file.parent / ".claude" / "guardrails" / f"{name}.md"
            src_files[path] = text
            target = path
            meta[entry_id_for(snap.sources, path) or str(path)] = {"type": "project-rules", "area": area, **base_meta}
        else:  # shared: master in the workspace, copy next to the file (unless that is the workspace)
            master = ws_root / "guardrails" / "shared" / f"{name}.md"
            if master.exists() and not same_text(master.read_text(encoding="utf-8"), text):
                raise RepoWriteError(f"guardrails/shared/{name}.md already exists with other content; rename the part")
            ws_files[master] = text
            meta[entry_id_for(snap.sources, master) or str(master)] = {
                "type": "project-rules", "area": area, "visibility": "shared", "owner": entry.owner}
            if same_repo:
                target = master
            else:
                target = file.parent / ".claude" / "guardrails" / "shared" / f"{name}.md"
                src_files[target] = text
                copies.append(Copy(master=_rel(master, ws_root), source=src.id, path=_rel(target, src.root)))
        if not in_imports:
            out.append("\n")
        out.append(f"@{_rel(target, file.parent)}\n")
        in_imports = True

    if skills:
        out.append("\n## On request (skills)\n" + "".join(f"- `{n}` — {h}\n" for n, h in skills))
    new_main = fm_text + "".join(out).lstrip("\n")
    src_files[file] = new_main
    meta[entry.id] = {"type": "index", "area": "docs", **base_meta}
    subject = f"Split {Path(entry.path).name} into {len(src_files) - 1} files"

    if same_repo:   # one commit: everything lives in the workspace repository
        for path, text in ws_files.items():
            src_files[path] = text
        update_manifest(ws_root, meta)
        result = commit_files(src, {**src_files, manifest_path(ws_root): manifest_path(ws_root).read_text(encoding="utf-8")},
                              subject, why, mode)
        return {"source": result, "workspace_commit": None, "files": [_rel(p, ws_root) for p in src_files]}

    result = commit_files(src, src_files, subject, why, mode)
    for path, text in ws_files.items():
        write_text(path, text)
    config = load_workspace(ws_root).config
    register(config, copies)
    written = [*ws_files, save_config(ws_root, config)]
    update_manifest(ws_root, meta)
    written.append(manifest_path(ws_root))
    ws_sha = commit_workspace(ws_root, written, f"Shared guardrails from {src.id}/{entry.path}", why)
    return {"source": result, "workspace_commit": ws_sha,
            "files": [_rel(p, src.root) for p in src_files] + [_rel(p, ws_root) for p in ws_files]}
