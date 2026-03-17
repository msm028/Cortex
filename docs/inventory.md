# Inventory

Last updated: 2026-03-17 20:09 (local)

## Hosts

- `majelis` (`192.168.1.124`): builder/dev workstation, local compose execution.
- `cortex-control` (`192.168.1.103`): control-plane host (hosted wiki, edge ingress, cloudflared tunnel).
- `cortex-data` (planned via IaC): state/secrets host for Postgres/MinIO/Vaultwarden.

## Services By Host

### majelis

- `core-postgres-1` (Postgres)
- `core-minio-1` (MinIO)
- `core-vaultwarden-1` (Vaultwarden)
- `edge-caddy-1` (edge reverse proxy)
- `edge-cloudflared-1` (Cloudflare tunnel)
- `caddymanager-backend` / `caddymanager-frontend` (Caddy Manager)

### cortex-control

- `wiki-wiki-1` (MkDocs static site)
- `wiki-wiki-proxy-1` (Caddy proxy on `:8085`)
- `edge-caddy-1` (if deployed on control host)

## Endpoints

- `http://cortex-control:8085` - hosted wiki
- `http://cortex-control:3001` - Uptime Kuma
- `http://vault.thecortexstack.com` - Vaultwarden via edge Caddy + Cloudflare
- `http://minio.thecortexstack.com` - MinIO console via edge Caddy + Cloudflare
- `http://majelis:8086` - Caddy Manager UI

## Source Of Truth Links

- Ports registry: `docs/runbooks/ports-registry.yaml`
- Edge compose: `bootstrap/compose/edge/docker-compose.yml`
- Wiki compose: `bootstrap/compose/wiki/docker-compose.yml`
- Proxmox IaC:
  - `infra/proxmox/cortex-control/`
  - `infra/proxmox/cortex-data/`
