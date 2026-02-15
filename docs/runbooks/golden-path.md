# Golden Path Runbook

## Prerequisites

- `PUBLIC_DOMAIN` is set in the shell environment.
- Docker daemon is available.

Example:

```bash
export PUBLIC_DOMAIN=thecortexstack.com
```

## Command

Run the end-to-end preflight and bootstrap sequence:

```bash
make bootstrap-check
```

## What It Validates

`make bootstrap-check` runs:

1. `make doctor`
2. `make smoke`
3. `make up`
4. `make plan TEMPLATE=stack-status ENV=dev`
5. `make plan TEMPLATE=ingress-status ENV=dev`

Final output line:

- `BOOTSTRAP-CHECK: PASS`
- `BOOTSTRAP-CHECK: FAIL (<step>)`

## Troubleshooting

- Use `make doctor` for environment readiness failures.
- Use `make logs-core SERVICE=<name>` or `make logs-edge SERVICE=<name>` for service diagnostics.
- Re-run failing sub-step directly to isolate root cause.

## Rollback

To stop running services started by this flow:

```bash
make down
```
