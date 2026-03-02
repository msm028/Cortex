# Deploy Uptime Kuma

## Purpose

Deploy Uptime Kuma on `cortex-control` to provide live service availability checks and a simple status UI.

This is the recommended first monitoring layer for Cortex because it solves the immediate question: is a service or route up right now?

## Why Uptime Kuma First

Use Uptime Kuma before Prometheus/Grafana when you need:

- live HTTP/TCP endpoint checks
- a simple uptime dashboard
- certificate expiry visibility
- lightweight alerting

Use Prometheus/Grafana later for metrics, dashboards, and long-term performance analysis.

## Placement

- Host: `cortex-control`
- Compose file: `bootstrap/compose/uptime-kuma/docker-compose.yml`
- Local UI: `http://cortex-control:3001/`

This fits ADR-0003: monitoring UI belongs on the control plane, not on `majelis`.

## Deploy

```bash
cd /opt/cortex
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml up -d
```

## Verify

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml ps
curl -fsS http://127.0.0.1:3001/ >/dev/null && echo "UPTIME-KUMA: PASS"
```

## Suggested First Monitors

Add these after first login:

- `Wiki`: `http://127.0.0.1:8085/`
- `Vaultwarden route`: `http://vault.thecortexstack.com`
- `MinIO route`: `http://minio.thecortexstack.com`
- `Caddy Manager`: `http://majelis:8086/`

If you want to keep checks internal first, prefer local/LAN URLs over public routes.

## Persistence

Uptime Kuma stores state in the named Docker volume `kuma_data`.

## Update

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml pull
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml up -d
```

## Rollback

```bash
docker compose -f bootstrap/compose/uptime-kuma/docker-compose.yml down
```

This removes the container but preserves monitor data in `kuma_data`.

## Next Step

After Uptime Kuma is stable, the next observability layer should be Prometheus plus Grafana for metrics and dashboards.
