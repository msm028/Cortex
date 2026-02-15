# Stack Status Runbook

## Purpose

Generate and execute a deterministic status-check plan for core and edge containers.

## Generate Plan

```bash
python3 ops/plan/mkplan.py --template stack-status
```

## Validate and Execute (Dry-Run Default)

```bash
make validate-plan PLAN=plans/<generated>.json
make execute PLAN=plans/<generated>.json
```

The template checks:

- running containers filtered to `core-` and `edge-` prefixes
- health polling for all running `core-`/`edge-` containers that define Docker health checks
- `edge-caddy-1` running status check

Smoke output ends with a single `STACK STATUS: PASS` or `STACK STATUS: FAIL`.

Health polling uses 2-second intervals and can take up to 120 seconds.
