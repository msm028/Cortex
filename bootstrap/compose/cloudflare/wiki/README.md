# Cloudflare Wiki Publisher

Publishes the hosted wiki through Cloudflare Tunnel using an Access-protected public hostname.

## Prerequisites

- `TUNNEL_TOKEN` from Cloudflare (store/retrieve via Vaultwarden, never commit values).
- Hosted wiki already serving locally on `http://localhost:8085`.

## Export Token (Manual, No Value In Repo)

```bash
export TUNNEL_TOKEN="<from-vaultwarden>"
```

## Run

```bash
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml up -d
```

## Logs

```bash
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml logs -f
```

## Rollback

```bash
docker compose -f bootstrap/compose/cloudflare/wiki/docker-compose.yml down
unset TUNNEL_TOKEN
```
