# CodeQL and Dependabot

## CodeQL

- Workflow: [codeql.yml](../../.github/workflows/codeql.yml). It runs on every push and PR to `main`
  and every Monday.
- Languages: `python` (application code) and `actions` (the workflows themselves).
- Query suite: `security-extended`, which adds lower-precision security queries on top of the
  default suite.
- Use this workflow (advanced setup) **instead of** the "Default setup" button in Settings →
  Code security, because the two cannot be enabled at the same time.

Patterns that commonly trigger CodeQL Python alerts, and how Vitreo avoids them:

| CodeQL query | How Vitreo avoids it |
|---|---|
| `py/log-injection` | Logs contain ids and enum values only, never request strings |
| `py/stack-trace-exposure` | The global 500 handler returns a fixed message |
| `py/clear-text-logging-sensitive-data` | Passwords and tokens are never logged |
| `py/weak-sensitive-data-hashing` | Passwords use scrypt, not MD5/SHA |
| `py/sql-injection` | Only SQLAlchemy parameterized queries |
| `py/hardcoded-credentials` | Secrets come from the environment; tests generate random ones |
| `actions/missing-workflow-permissions` | Every workflow declares least-privilege `permissions` |

### Alert log

| Alert | Severity | File | Fix | Commit |
|---|---|---|---|---|
| _Fill after the first scan (Security → Code scanning)_ | | | | |

## Dependabot

- Config: [dependabot.yml](../../.github/dependabot.yml), weekly updates for `pip` and `github-actions`.
- Also enable in Settings → Code security: **Dependabot alerts** and **Dependabot security updates**.
- Evidence required: at least one Dependabot PR, reviewed and merged with the CI green.

## Screenshots (`docs/evidencias/sesion14/`)

- `codeql-0-alerts.png`: Security → Code scanning with 0 open critical alerts.
- `codeql-workflow.png`: green CodeQL run.
- `dependabot-pr.png`: a Dependabot PR with green checks.
