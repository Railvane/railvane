# Railvane in pull requests

Add `.github/workflows/guardrails.yml` to a repository with guardrails:

```yaml
name: Guardrails
on: pull_request

jobs:
  railvane:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0          # full history, for the 'stale' check
      - uses: Railvane/railvane@main
        with:
          fail-on: error          # error | warning | info | never
```

Findings appear as annotations on the changed files. A shared guardrail that contains
a token, password or private key fails the check (`share-secret`); IP addresses, e-mail
addresses and personal paths are warnings (`share-personal`).

## Rules

| Rule | Level | What |
|---|---|---|
| `frontmatter-invalid` | error | Railvane frontmatter does not match the schema |
| `share-secret` | error | shared file contains a token, key or password |
| `share-personal` | warning | shared file contains an IP, e-mail address or personal path |
| `file-too-long` | warning | more lines than `lint.max_lines` (300) |
| `token-heavy` | warning | more tokens than `lint.max_tokens` (2000) |
| `dead-link` | warning | `[[link]]` or `.md` link that does not resolve |
| `duplicate-rule` | warning | the same rule appears in more than one file |
| `stale` | info | not changed in `lint.stale_days` (180) days |
| `unconfirmed` | info | metadata is guessed, not confirmed |

Ignore a rule everywhere in `railvane.yaml`:

```yaml
lint:
  ignore: [stale]
```

or in one file with `<!-- railvane-ignore: duplicate-rule -->`.

Run the same check locally with `railvane lint .`.
