# Railvane — working agreements

Railvane is an open-source project. Everything in this repository is in **English**:
code, comments, commit messages, docs and UI texts.

## Architecture
- **No database.** Git is the store: markdown files, `railvane.yaml`, sidecar manifests, `git log`.
  Indexes are built in memory; caches must be disposable.
- The only other state is the **data dir** (`RAILVANE_DATA`, `/data` in Docker): the instance id and, later,
  the link to a hub (webheaven-kit product contract). Never content.
- Admin module: `railvane/admin.py` fills in the webheaven-kit `AdminProvider`; the UI uses `@webheaven/kit/admin`.
- Backend: Python package `railvane/` (FastAPI). Frontend: `web/` (React + Vite), built into `railvane/static`.
- One small container: Python + git CLI. Never add services that need state.
- Never rewrite a user's source file without an explicit action (commit or PR).

## Conventions
- Files over 300 lines are a signal to split.
- Schema changes: update `docs/schema.md` and bump the schema version when breaking.
- Every change to behaviour gets a test (`python -m pytest`).
- Vite builds do not catch undefined variables — check imports before pushing.

## Commands
- Tests: `.venv/Scripts/python -m pytest` (Windows) / `.venv/bin/python -m pytest`
- UI build: `cd web && npm run build`
- Run: `railvane serve <folder>` (default port 8484)
- Image: `docker build -t railvane .`
