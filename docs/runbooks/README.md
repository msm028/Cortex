# Runbooks Index

## Available Runbooks

- [Repository Validator](./validator.md): deterministic repository checks used by `make validate`.
- [Development Setup](./dev-setup.md): Python version pin, dependency install, and smoke preflight.
- [Plan Validate Execute](./plans.md): deterministic plan lifecycle and execution audit flow.
- [Bootstrap Core](./bootstrap-core.md): core compose stack definition and dry-run validation flow.
- [Edge Access](./edge-access.md): cloudflared + Caddy ingress flow and dry-run validation.
- [Stack Status](./status.md): stack-status and ingress-status smoke checks for local stack and Cloudflare ingress.
- [Smoke Preflight](./smoke.md): deterministic preflight checks with fail-fast final PASS/FAIL.
- [Testing](./testing.md): how to run deterministic unit tests with `make test`.

## Repo Skills Location

Project-level Codex guidance lives in:

- `.agents/skills/00-cortex-operating-rules.md`
- `.agents/skills/01-build-chunk-template.md`
