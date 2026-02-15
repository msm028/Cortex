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
- `PUBLIC_DOMAIN` presence (yes/no only)

## PASS/FAIL Meaning

- `DOCTOR: PASS`: required local prerequisites are present.
- `DOCTOR: FAIL`: one or more required checks failed.

## Common Fixes

- Docker daemon down/unreachable:
  - start Docker service/desktop and retry `make doctor`
- Wrong directory:
  - run from repo root where `Makefile` and compose files exist
- Missing `PUBLIC_DOMAIN`:
  - export a value, for example:
    - `export PUBLIC_DOMAIN=thecortexstack.com`
- Missing compose files:
  - restore files from git and verify branch state
