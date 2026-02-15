# Doctor Diagnostics Runbook

## When To Run

Run `make doctor` before bootstrap, troubleshooting, or handoff when you want a quick environment readiness check.

## What It Checks

- git branch and working tree status entry count
- Docker CLI availability
- Docker Compose availability
- required compose files:
  - `bootstrap/compose/core/docker-compose.yml`
  - `bootstrap/compose/edge/docker-compose.yml`
- concise `core-` / `edge-` container snapshot
- required environment variables via `make env-check`

## Required Environment Variables

- `PUBLIC_DOMAIN`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `VAULTWARDEN_DATABASE_URL`
- `VAULTWARDEN_ADMIN_TOKEN`
- `VAULTWARDEN_DOMAIN`
- `VAULTWARDEN_SIGNUPS_ALLOWED`
- `TUNNEL_TOKEN`

Set variables in the current shell/session only and do not commit secrets to the repository. Use secure secret storage (for example Vaultwarden) for secret source-of-truth.

## PASS/FAIL Meaning

- `DOCTOR: PASS`: required local prerequisites are present.
- `DOCTOR: FAIL`: one or more required checks failed.

## Common Fixes

- Docker daemon down/unreachable:
  - start Docker service/desktop and retry `make doctor`
- Wrong directory:
  - run from repo root where `Makefile` and compose files exist
- Missing environment variables:
  - export required names in the shell/session before retrying
- Missing compose files:
  - restore files from git and verify branch state
