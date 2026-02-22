# ARCHITECTURE

## Purpose
Cortex is a governed Plan → Validate → Execute platform for building and operating infrastructure safely.
Deterministic scripts decide; humans approve destructive/prod actions.

## As-Built (Phase 2 Close-Out) — February 2026

### Runtime Topology (current)
Bootstrap runs on **majelis** as the builder/control workstation (temporary until dedicated VMs exist). This is an intentional bootstrap constraint.【00-current-infra.md】

- **edge stack (docker compose)**
  - `cloudflared` (Cloudflare Tunnel connector)
  - `caddy` (host routing)

- **core stack (docker compose)**
  - `vaultwarden` (secrets source of truth)
  - `postgres` (state/metadata, pgvector-ready later)
  - `minio` (object storage / terraform backend target)

### Ingress
Cloudflare Tunnel → Caddy (host routing) → core services.

Hostnames:
- `vault.<PUBLIC_DOMAIN>` → vaultwarden
- `minio.<PUBLIC_DOMAIN>` → minio console

### Deterministic Control Surface
Operator entrypoints:
- `make smoke` (repo deterministic checks)
- `make doctor` (local diagnostics)
- `make plan TEMPLATE=stack-status|ingress-status` (health smoke checks)
- `make vw-doctor / vw-up / vw-run` (Vaultwarden-backed runtime injection)

Auditing:
- all executions write audit artifacts to `artifacts/audit/`

### Secrets Model (as-built)
No secret values in Git or plans. Repo stores **Vaultwarden item IDs + selectors** only in:
- `ops/env/vaultwarden-map.json`

Secrets are injected at runtime using BW CLI session (`BW_SESSION`) and `vw-run`.

## Target Architecture (post Phase 3+)
Master design target is multi-VM:
- cortex-control (MAF/MCP/wiki)
- cortex-data (postgres/minio/vault)
- cortex-dev
- cortex-prod
Optional: cortex-edge
(See Master Design v2.4.3.)

## Phase Exit Criteria Tracking
### Phase 2 (Core Services)
Required:
- Vaultwarden, Postgres, MinIO running
- runtime secret injection working via vw-run / vw-up
- backup + restore test verified
- no secrets stored in repo

Evidence should be recorded as:
- latest audit filenames for backup-core and restore-test
- last `make smoke` pass
