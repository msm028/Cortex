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
- Caddy TCP listen check on `edge-caddy-1` container IP port `80`
- HTTP `HEAD /` route checks through Caddy with:
  - `Host: vault.{PUBLIC_DOMAIN}`
  - `Host: minio.{PUBLIC_DOMAIN}`

Smoke output ends with a single `STACK STATUS: PASS` or `STACK STATUS: FAIL`.

Health polling uses 2-second intervals and can take up to 120 seconds.

## Route Check Expectations

Route checks are considered good when response status is non-`404` and non-`5xx`.

- Expected good examples: `200`, `301`, `302`, `401`, `403`
- Failure statuses: `404`, `500`, `502`, `503`, `504`

## Troubleshooting

- `404` usually means host routing mismatch in Caddyfile or `PUBLIC_DOMAIN` mismatch.
- `502`/`503` usually means upstream service is not reachable/ready from Caddy.
