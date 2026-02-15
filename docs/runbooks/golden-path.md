# Golden Path Runbook

## Prerequisites

- required environment variables are set in the shell/session.
- Docker daemon is available.

Example:

```bash
export PUBLIC_DOMAIN=thecortexstack.com
```

## Required Environment Variables

- `PUBLIC_DOMAIN`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `VAULTWARDEN_ADMIN_TOKEN`
- `TUNNEL_TOKEN`

Set these per shell/session and do not commit values. Store and manage secrets via a secure manager (for example Vaultwarden).

## Command

Run the end-to-end preflight and bootstrap sequence:

```bash
make bootstrap-check
```

## What It Validates

`make bootstrap-check` runs:

1. `make doctor`
2. `make smoke`
3. `make env-check`
4. `make up`
5. `make plan TEMPLATE=stack-status ENV=dev`
6. `make plan TEMPLATE=ingress-status ENV=dev`

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
