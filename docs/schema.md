# Schema v1

## Guardrail frontmatter

```markdown
---
type: memory
area: deploy
visibility: shared
owner: "@bart"
tags: [deploy, production]
status: active
scope: project:homeplatform
---
# Never deploy without an explicit order
```

| Field | Required | Values |
|---|---|---|
| `type` | yes | `project-rules`, `memory`, `skill`, `agent`, `index` |
| `area` | yes | a lifecycle area id, see below |
| `visibility` | yes | `private` (only you) or `shared` (may leave your machine in a pack) |
| `owner` | yes | person or team, e.g. `@bart` or `@platform-team` |
| `tags` | no | list of free-form tags |
| `status` | no | `draft`, `active` (default), `deprecated` |
| `scope` | no | free text, e.g. `global`, `org:nipv`, `project:homeplatform` |

Other keys (such as `name` and `description` used by Claude Code memory files) are kept as-is.

Files without frontmatter — for example an existing `CLAUDE.md` — are never rewritten.
Their metadata lives in a sidecar manifest (phase 1).

## Lifecycle areas

| Phase | Areas |
|---|---|
| Idea & discovery | `ideation`, `requirements`, `priority` |
| Design | `architecture`, `ux`, `data`, `api` |
| Build | `coding`, `stack`, `git`, `review`, `deps`, `ai` |
| Quality & security | `testing`, `security`, `privacy`, `i18n` |
| Release & deploy | `cicd`, `versioning`, `deploy`, `config` |
| Operations | `monitoring`, `incident`, `backup`, `maintenance`, `docs` |

The catalogue is advisory. Not every area needs guardrails — fewer, sharper rules work better for agents.

## railvane.yaml

See [examples/railvane.yaml](../examples/railvane.yaml). Unknown keys are reported as errors,
so typos do not go unnoticed.
