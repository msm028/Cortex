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

## Cloudflare Setup (UI)

1. Ensure your domain is an active zone in Cloudflare.
2. In Cloudflare Zero Trust, create a Tunnel and obtain its token.
3. Configure public hostname routes for the tunnel (single hostnames or wildcard, as needed).
4. For each hostname, create an Access self-hosted application.
5. Add an explicit Allow policy for expected users/groups; default posture should remain deny.

## Operational Templates

- Bring edge up:
  - `python3 ops/plan/mkplan.py --template edge-up`
- Bring edge down:
  - `python3 ops/plan/mkplan.py --template edge-down`

Validate, approve, and execute via standard governance flow:

```bash
make validate-plan PLAN=plans/<generated>.json
make approve PLAN=plans/<generated>.json VAULTWARDEN_ITEM_ID=<id>
make execute PLAN=plans/<generated>.json
```

`TUNNEL_TOKEN` is supplied via environment variable for `cloudflared`. Store only Vaultwarden item ID references in repo docs/plans; do not store token values.
