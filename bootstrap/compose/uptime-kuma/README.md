# Uptime Kuma Compose Bundle

## Purpose

Run Uptime Kuma on `cortex-control` as the first live service health dashboard for Cortex.

## Compose File

- `bootstrap/compose/uptime-kuma/docker-compose.yml`

## Deploy

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml up -d
```

## Verify

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml ps
curl -fsS http://127.0.0.1:3001/ >/dev/null && echo "UPTIME-KUMA: PASS"
```

## Update

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml pull
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml up -d
```

## Rollback

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml down
```

Persistent state is stored in the named volume `kuma_data`.
