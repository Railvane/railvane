"""Minimal GitHub REST client (standard library only): enough to open a pull request."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"


def token() -> str | None:
    return os.environ.get("RAILVANE_GITHUB_TOKEN")


def create_pull(slug: str, head: str, base: str, title: str, body: str) -> str:
    """Open a pull request and return its URL."""
    req = urllib.request.Request(
        f"{API}/repos/{slug}/pulls", method="POST",
        data=json.dumps({"title": title, "head": head, "base": base, "body": body}).encode(),
        headers={"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "railvane"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)["html_url"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"GitHub refused the pull request ({e.code}): {detail}") from e


def compare_url(slug: str, base: str, head: str) -> str:
    return f"https://github.com/{slug}/compare/{base}...{head}?expand=1"
