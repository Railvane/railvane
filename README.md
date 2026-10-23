<p align="center"><img src="web/public/railvane-logo.svg" width="96" alt="Railvane"></p>

<h1 align="center">Railvane</h1>
<p align="center"><b>The guardrails manager for AI coding agents.</b></p>

Railvane gives you one clear view of the instructions your AI coding agents follow —
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, memory files, skills and agent prompts — across all your repositories.

- **Git is the store.** No database. Your guardrails stay plain markdown in your own repositories.
- **History with the why.** Every change is a commit with a reason, so old agreements stay explainable.
- **Quality checks.** Duplicates, dead links, stale rules, oversized files, token budgets — locally, in the UI and in CI.
- **Share safely.** Private vs shared per file, a share check for secrets and personal data, and versioned packs for teams.

> **Status:** v0.4 — the MVP is complete; expect rough edges.

## What you get

| View | What it does |
|---|---|
| **Repositories** | Which repositories Railvane reads and writes: branch, remote, last commit, uncommitted changes. Add sources here. |
| **Library** | All guardrails across your sources as cards, with filters, search and a reader (links, backlinks, metadata). |
| **Classify** | Railvane guesses type and lifecycle area per file; you confirm. Metadata goes to `.railvane/manifest.yaml` — source files are never rewritten. |
| **Timeline** | Every change across all repositories, with its diff and the *why*. Revert with one click. |
| **Quality** | Lint findings: share check, duplicates, dead links, token budget, stale rules. |
| **Packs** | Install other teams' guardrails pinned to a version; review upstream updates per rule; keep your own overrides; publish your own packs. |

Edits are a direct commit, or a branch + pull request for git sources. Every edit asks *why*.

### Split, share and promote

- **Split** a large file such as `CLAUDE.md`: one part per section, each kept inline, moved to
  `.claude/guardrails/` (project), made **shared** (master in your workspace under `guardrails/shared/`,
  a copy in the repository) or turned into a **skill** that agents load only when needed. The original
  becomes a list of `@imports`. Metadata goes to the sidecar, not into the files — agents read
  frontmatter too, and it would cost tokens in every session.
- **Copies**: Railvane knows which file is a copy of which master (`copies:` in `railvane.yaml`), shows
  when a copy is out of date (`copy-drift`) and syncs all copies with one commit per repository.
- **Promote to rule**: a memory note (Claude Code memory has types like *feedback* and *project*)
  becomes a real guardrail in your workspace; the memory is marked as promoted.

## Quick start

A workspace is a git repository with a `railvane.yaml` — see [examples/railvane.yaml](examples/railvane.yaml)
and the [schema](docs/schema.md).

```bash
pip install .                   # from a clone; not on PyPI yet
railvane serve path/to/workspace
```

Then open http://127.0.0.1:8484. Or with Docker:

```bash
docker run --rm -p 8484:8484 -v "$PWD:/workspace" ghcr.io/railvane/railvane:edge
```

Mount other repositories read-only and list them as sources with `readonly: true`.

| Environment variable | Purpose |
|---|---|
| `RAILVANE_GIT_NAME`, `RAILVANE_GIT_EMAIL` | Author of commits made by Railvane |
| `RAILVANE_GITHUB_TOKEN` | Push to git sources and open pull requests |
| `RAILVANE_CACHE` | Where git sources are cloned (disposable; default `~/.cache/railvane`) |
| `RAILVANE_HISTORY_MIRROR=1` | Docker on Windows/macOS: git history of mounted folders is slow; keep a fast copy in the cache (mount the cache as a volume) |
| `RAILVANE_PATH_MAP` | Show host paths instead of container paths, e.g. `/workspace=C:/Projects/guardrails` |
| `RAILVANE_DATA` | Small data directory for the instance id and the link to a hub (`/data` in Docker; never content) |
| `RAILVANE_ADMIN_PASSWORD` | Server mode: required to link to or unlink from a hub (without it, linking is disabled) |
| `RAILVANE_RELEASES_FEED` | Release feed for *Check for updates* (default webheaven.nl; empty = off) |

## On a server

In server mode the workspace is a git URL: Railvane clones it, pulls every minute (and on
*Fetch & rescan*) and pushes every change it makes. Nothing lives only on the server.

```bash
railvane serve --git https://github.com/your-org/guardrails.git
```

or with Docker: see [compose.server.yaml](compose.server.yaml). Use git URLs for sources on a
server; a local folder from `railvane.yaml` that does not exist there is shown as *not available
here*, so one workspace works both on your laptop and on the server.

## Admin and linking to a hub

**Admin** (⚙ in the sidebar) shows status, usage, the audit trail (git) and a *Check for updates* button: only when
you click, your browser fetches the release feed anonymously.

Railvane works standalone and never contacts a hub on its own. Under **Admin › Link** you can link it to a hub
such as [webheaven.nl](https://webheaven.nl): Railvane requests a code, you approve it on the hub and choose what the
hub may see (health, statistics or full). You can change that or unlink at any time. Every call between Railvane and
the hub is listed under **Traffic**, with all data that went over the wire (secrets masked). Railvane keeps working
normally while a code waits for approval. Protocol: the
[webheaven-kit product contract](https://github.com/webheaven-platform/webheaven-kit/blob/main/docs/contract.md).

## In CI

```bash
railvane lint . --fail-on error      # text, --format json or --format github
```

or use the GitHub Action — see [docs/github-action.md](docs/github-action.md).

## Packs

A pack is a folder with `railvane-pack.yaml` (`name`, `description`, `license`) and markdown rules.
Versions are git tags (`v1.2.0`, or `<folder>/v1.2.0` for a pack in a sub folder). List packs you
publish under `publish:` and packs to offer under `catalog:` in `railvane.yaml`.

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

## License

[Apache-2.0](LICENSE)
