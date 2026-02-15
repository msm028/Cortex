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
- health polling for core containers (`postgres`, `minio`, `vaultwarden`)
- `edge-caddy-1` running status

Core health polling uses 2-second intervals and can take up to 120 seconds.
