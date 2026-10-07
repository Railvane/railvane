"""Quality checks for guardrails. Pure functions over an index snapshot."""

from .runner import Finding, run_lint, summarize

__all__ = ["Finding", "run_lint", "summarize"]
