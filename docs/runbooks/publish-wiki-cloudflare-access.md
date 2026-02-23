# Publish Wiki With Cloudflare Access

## Purpose

Expose the hosted wiki via Cloudflare Tunnel + Access while keeping the origin private.

## Cloudflare Setup Order

1. Create/verify an Access application first for the wiki hostname.
2. Create a tunnel (or reuse an existing one) and obtain a tunnel token.
3. Add a public hostname in the tunnel config that points to:
   - `http://localhost:8085`

## Runtime

Use `TUNNEL_TOKEN` at runtime and start cloudflared with token auth:

```bash
export TUNNEL_TOKEN="<from-vaultwarden>"
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml up -d
```

The compose service runs:

```text
cloudflared tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
```

## Persist The Tunnel Token

For persistent service operation on `cortex-control`, store the token in a root-only env file:

```bash
sudo install -d -m 700 /etc/cortex
sudo sh -c 'umask 177 && cat > /etc/cortex/cloudflared-wiki.env <<EOF
TUNNEL_TOKEN=<value>
EOF'
sudo chown root:root /etc/cortex/cloudflared-wiki.env
sudo chmod 600 /etc/cortex/cloudflared-wiki.env
```

Then launch with the env file:

```bash
sudo docker compose \
  -f bootstrap/compose/cloudflare/wiki/docker-compose.yml \
  --env-file /etc/cortex/cloudflared-wiki.env \
  up -d
```

## Why This Works

- Tunnel is outbound-only from `cortex-control` to Cloudflare.
- No inbound firewall port open is required for public access.
- Origin remains local (`localhost:8085`) behind Cloudflare Access policy.

## Operations

Check status/logs:

```bash
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml ps
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml logs -f
```

Rollback:

```bash
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml down
unset TUNNEL_TOKEN
```

If using persisted token storage, remove it when decommissioning:

```bash
sudo rm -f /etc/cortex/cloudflared-wiki.env
```
