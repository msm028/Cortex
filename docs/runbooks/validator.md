# Repo Validator Runbook

## Purpose

`ops/validator/validate_repo.py` is a deterministic repository validator used by `make validate`.

## Run

```bash
make validate
```

Or run directly:

```bash
python3 ops/validator/validate_repo.py
```

## Checks

The validator fails if any of the following conditions are not met:

- Required directories exist:
  - `bootstrap/compose`
  - `bootstrap/env`
  - `infra/modules`
  - `infra/backend`
  - `infra/environments/dev`
  - `infra/environments/prod`
  - `ops/validator`
  - `ops/health`
  - `ops/backup`
  - `ops/audit`
  - `policies`
  - `skills`
  - `scripts`
  - `plans`
  - `artifacts`
  - `docs/decisions`
  - `docs/runbooks`
  - `n8n/dev`
  - `n8n/prod`
- Required files exist:
  - `.gitignore`
  - `.editorconfig`
  - `Makefile`
  - `README.md`
  - `docs/inventory.md`
  - `docs/CHANGELOG.md`
- `.env` is not tracked in git (`git ls-files` check).
- `.gitignore` includes both `plans/` and `artifacts/`.
- No tracked file contains private key markers:
  - `BEGIN PRIVATE KEY`
  - `BEGIN OPENSSH PRIVATE KEY`

## Exit Codes

- `0`: all checks passed
- `1`: one or more checks failed
