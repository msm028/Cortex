# Edge / Access Runbook

## Purpose

The edge stack uses Cloudflare Tunnel and Caddy as the single routing source of truth.

- Tunnel ingress: `cloudflared`
- Explicit routing: `bootstrap/compose/edge/Caddyfile`
- Internal upstreams: core services on shared Docker network

## Why No Inbound Ports

No host ports are published by default. Inbound traffic should come through Cloudflare Tunnel, reducing direct edge exposure.

## Traffic Flow

1. User reaches Cloudflare hostname.
2. Cloudflare Access policy authenticates user.
3. Cloudflare Tunnel forwards traffic to Caddy.
4. Caddy routes request to internal core services:
   - `vault.{$PUBLIC_DOMAIN}` -> `vaultwarden:80`
   - `minio.{$PUBLIC_DOMAIN}` -> `minio:9000`

## Dry-Run Validation

Generate and run the edge dry-run plan:

```bash
python3 ops/plan/mkplan.py --template edge-dry-run
make validate-plan PLAN=plans/<generated>.json
make execute PLAN=plans/<generated>.json
```

Execution defaults to dry-run and only writes audit output.
