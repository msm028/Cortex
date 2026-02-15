# Smoke Preflight Runbook

## Purpose

Run a deterministic preflight sequence before operational work.

## When To Run

Run `make smoke` before plan execution changes, CI handoff, or release candidate checks.

## What It Checks

`make smoke` runs, in order:

1. `make validate`
2. `make test`
3. `make plan TEMPLATE=stack-status ENV=dev DRY_RUN=true`
4. `make plan TEMPLATE=ingress-status ENV=dev DRY_RUN=true`

The target is fail-fast and prints one final line:

- `SMOKE: PASS`
- `SMOKE: FAIL (<step-name>)`

## Expected Output

On success, the final line is:

```text
SMOKE: PASS
```

If a step fails, the final line is:

```text
SMOKE: FAIL (<step-name>)
```

## Audit Notes

`make smoke` only validates/tests and generates plan files; it does not execute plans, so it does not create new audit entries by itself.

Execution audits are written to:

- `artifacts/audit/*.audit.json`

To locate the latest audit file:

```bash
ls -1t artifacts/audit/*.audit.json | head -n 1
```
