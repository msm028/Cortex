# Runbooks Index

## Available Runbooks

- [Repository Validator](./validator.md): deterministic repository checks used by `make validate`.
- [Changelog And Release Notes](./changelog.md): generate release-note artifacts and maintain `CHANGELOG.md`.
- [Doctor Diagnostics](./doctor.md): quick operator diagnostics for git/docker/compose/files/env readiness.
- [Bitwarden CLI](./bw-cli.md): install and configure bw CLI for Vaultwarden-backed env injection.
- [Development Setup](./dev-setup.md): Python version pin, dependency install, and smoke preflight.
- [Environment Variables](./env-vars.md): compose-derived env variable manifest with required/secret hints.
- [Golden Path](./golden-path.md): end-to-end bootstrap-check sequence with PASS/FAIL result.
- [Ops Commands](./ops-commands.md): deterministic make wrappers for up/down/restart/logs operations.
- [Ports And Service Map](./ports-and-service-map.md): shared port ownership map and pre-start conflict checks.
- [Vaultwarden Env](./vaultwarden-env.md): bw-based env injection for required runtime variables.
- [Vaultwarden Recovery](./vaultwarden.md): crashloop triage and sqlite recovery procedure for missing `twofactor`.
- [Backups And Restore Test](./backups.md): restic backup to MinIO and non-destructive restore verification.
- [Plan Validate Execute](./plans.md): deterministic plan lifecycle and execution audit flow.
- [Bootstrap Core](./bootstrap-core.md): core compose stack definition and dry-run validation flow.
- [Edge Access](./edge-access.md): cloudflared + Caddy ingress flow and dry-run validation.
- [Stack Status](./status.md): stack-status and ingress-status smoke checks for local stack and Cloudflare ingress.
- [Smoke Preflight](./smoke.md): deterministic preflight checks with fail-fast final PASS/FAIL.
- [Testing](./testing.md): how to run deterministic unit tests with `make test`.

## Validation

- `make validate-codex-config`: validates `.codex/config.toml` by running Python 3.11 in Docker and parsing TOML with `tomllib`.

## Repo Skills Location

Project-level Codex guidance lives in:

- `.agents/skills/00-cortex-operating-rules.md`
- `.agents/skills/01-build-chunk-template.md`
