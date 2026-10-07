<p align="center"><img src="web/public/railvane-logo.svg" width="96" alt="Railvane"></p>

<h1 align="center">Railvane</h1>
<p align="center"><b>The guardrails manager for AI coding agents.</b></p>

Railvane gives you one clear view of the instructions your AI coding agents follow —
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, memory files, skills and agent prompts — across all your repositories.

- **Git is the store.** No database. Your guardrails stay plain markdown in your own repositories.
- **History with the why.** Every change is a commit with a reason, so old agreements stay explainable.
- **Quality checks.** Contradictions, duplicates, stale rules, oversized files, token budgets.
- **Share safely.** Private vs shared per file, a share check for secrets and personal data, and versioned packs for teams.

> **Status:** early development (phase 0 of the MVP). Not usable yet.

## Quick start

```bash
pip install railvane            # not published yet — see Development
railvane serve path/to/your/repo
```

Then open http://127.0.0.1:8484.

### Docker

```bash
docker run --rm -p 8484:8484 -v "$PWD:/workspace:ro" ghcr.io/railvane/railvane:edge
# or: RAILVANE_WORKSPACE=path/to/repo docker compose up -d
```

## Configuration

Put a `railvane.yaml` in the root of your workspace — see [examples/railvane.yaml](examples/railvane.yaml)
and the [schema](docs/schema.md). Without one, Railvane uses sensible defaults.

## Development

Everything in Docker, with auto-reload (UI on :5173, API on :8484):

```bash
docker compose -f compose.dev.yaml up
```

Or without Docker:

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest

cd web && npm install && npm run dev   # UI on :5173, proxies /api to :8484
railvane serve .                       # API on :8484
```

`npm run build` writes the UI into `railvane/static`, which `railvane serve` then serves.

## Roadmap

| Version | Focus |
|---|---|
| v0.1 | Import and see: library, reader, private/shared |
| v0.2 | History with the why, light edits as commit or PR |
| v0.3 | Quality: lint, share check, CLI + GitHub Action |
| v0.4 | Packs: install, update and publish guardrail sets |

## License

[Apache-2.0](LICENSE)
