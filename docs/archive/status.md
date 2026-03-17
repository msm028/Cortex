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

## Public Ingress Checks

Use the public ingress plan when you want external Cloudflare endpoint validation (not just container-level status checks).

```bash
python3 ops/plan/mkplan.py --template ingress-status
make validate-plan PLAN=plans/<generated>.json
make execute PLAN=plans/<generated>.json
```

The ingress plan checks:

- `https://vault.{PUBLIC_DOMAIN}/` with HTTPS `HEAD /`
- `https://minio.{PUBLIC_DOMAIN}/` with HTTPS `HEAD /`
- TLS verification with default system trust store
- status code, key headers (`server`, `cf-ray` when present), and elapsed time

Expected good outcomes:

- status code is one of `200`, `302`, `403`
- `server` header contains `cloudflare` (case-insensitive)
- `302`/`403` are valid when Cloudflare Access policy is in front

Troubleshooting public failures:

- DNS issue: hostname does not resolve as expected.
- Tunnel issue: Cloudflare Tunnel is down or token/config mismatch.
- Access issue: unexpected auth policy behavior (for example missing `302`/`403` where expected).
- Origin issue: upstream service unreachable/returning `5xx` behind tunnel.
