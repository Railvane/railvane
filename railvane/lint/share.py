"""Share check: things that must not leave your machine in a shared guardrail."""

from __future__ import annotations

import re

SECRETS = [
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("password", re.compile(r"(?i)\b(?:password|passwd|wachtwoord|secret|api[_-]?key)\b\s*[:=]\s*['\"]?[^\s'\"]{6,}")),
]

IPV4 = re.compile(r"(?<![\w.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\w.])")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
HOME_PATH = re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+|/home/[a-z_][a-z0-9_-]*|/Users/[A-Za-z][\w.-]*")

SAFE_IPS = {"127.0.0.1", "0.0.0.0", "255.255.255.255"}
SAFE_EMAIL = re.compile(r"(?i)noreply|no-reply|@example\.(?:com|org|net)$|@localhost")


def scan(text: str) -> list[tuple[int, str, str]]:
    """Return (line, severity, message) for every problem found."""
    found = []
    for n, line in enumerate(text.splitlines(), start=1):
        for label, pat in SECRETS:
            if pat.search(line):
                found.append((n, "error", f"possible {label}"))
        for m in IPV4.finditer(line):
            if m.group(1) not in SAFE_IPS:
                found.append((n, "warning", f"IP address {m.group(1)}"))
        for m in EMAIL.finditer(line):
            if not SAFE_EMAIL.search(m.group(0)):
                found.append((n, "warning", f"e-mail address {m.group(0)}"))
        for m in HOME_PATH.finditer(line):
            found.append((n, "warning", f"personal path {m.group(0)}"))
    return found
