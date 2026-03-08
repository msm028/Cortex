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

## Seeded Monitors

The repo includes a seed script for the baseline monitor set:

- `Wiki (local)` -> `http://127.0.0.1:8085/`
- `Vaultwarden (public)` -> `http://vault.thecortexstack.com`
- `MinIO (public)` -> `http://minio.thecortexstack.com`
- `Caddy Manager (LAN)` -> `http://192.168.1.124:8086/`

Run it from `majelis` with Vaultwarden injection active:

```bash
cd /home/maher/repos/cortex
make vw-run CMD="make uptime-kuma-seed"
```

Behavior:

- creates missing baseline monitors
- skips monitors that already exist by name
- does not delete or rewrite unrelated monitors

## Reseed Procedure

Use reseed when:

- the Uptime Kuma database was rebuilt
- the baseline monitor set drifted
- a fresh control-plane host is being prepared

Procedure:

```bash
cd /home/maher/repos/cortex
export BW_SESSION="$(bw unlock --raw)"
make vw-check
make vw-run CMD="make uptime-kuma-seed"
```

Expected result:

- `UPTIME-KUMA-SEED: PASS`

## Verify Baseline Monitors

Check that the repo-managed monitor set still exists:

```bash
cd /home/maher/repos/cortex
export BW_SESSION="$(bw unlock --raw)"
make vw-check
make vw-run CMD="make uptime-kuma-verify"
```

Expected result:

- `[OK]` for each baseline monitor
- `UPTIME-KUMA-VERIFY: PASS`
- `artifacts/status/uptime-kuma-live.json` refreshed for the generated ops status page

## Monitor Ownership

Ownership is split deliberately:

- repo-managed baseline monitors:
  - seeded by `ops/bin/uptime_kuma_seed.js`
  - safe to recreate through the reseed command
- operator-managed monitors:
  - ad hoc checks added directly in the Uptime Kuma UI
  - not modified or removed by the seed script

Rule:

- if a monitor belongs to the baseline operational footprint, add it to the seed script
- if a monitor is experimental or temporary, create it in the UI only

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
