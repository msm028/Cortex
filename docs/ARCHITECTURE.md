# ARCHITECTURE

## Purpose
Cortex Governor is a governed Plan → Validate → Execute platform for building and operating infrastructure safely.
Deterministic scripts decide; humans approve destructive and higher-risk actions.

Cortex Governor is an infrastructure and documentation product. It is not the home for application source code belonging to future projects.

## As-Built (Phase 2 Close-Out) — February 2026

### Runtime Topology (current)
Bootstrap runs on **majelis** as the builder/control workstation (temporary until dedicated VMs exist). This is an intentional bootstrap constraint.【00-current-infra.md】

- **edge stack (docker compose)**
  - `cloudflared` (Cloudflare Tunnel connector)
  - `caddy` (service routing on shared Docker network)

- **core stack (docker compose)**
  - `vaultwarden` (secrets source of truth)
  - `postgres` (state/metadata, pgvector-ready later)
  - `minio` (object storage / terraform backend target)

### Ingress
Cloudflare Tunnel → Caddy (service routing on shared Docker network) → core services.

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

## Product Direction

Cortex Governor is explicitly aimed at being the reusable infra and auto-wiki product inside **The Cortex Stacks** family.

That means:

- Cortex Governor owns shared infrastructure automation, ingress, documentation, and platform services.
- Future projects keep their application code in separate repositories.
- Cortex Governor consumes project-level infrastructure manifests instead of absorbing project logic directly.

This direction reduces control-plane drift and keeps the repo reusable across more than one app.

## Target Architecture

### Host Roles

- `majelis`: operator and development workstation where plans are authored, validated, and reviewed
- `cortex-control`: shared control plane for ingress, hosted wiki, monitoring, and platform control services
- `cortex-data`: shared state and secret-bearing services
- project runtime hosts: isolated hosts or VMs for project-specific frontend, backend, and worker services

### Shared Platform Services

Target shared services managed by Cortex over time:

- ingress and route management through Caddy
- Vaultwarden
- PostgreSQL
- pgvector
- Redis
- MinIO
- LiteLLM
- Langfuse
- OpenTelemetry Collector
- hosted wiki and operational status publishing

### Project Integration Model

Each project should provide a machine-readable infrastructure contract, then Cortex should:

1. provision or select runtime targets
2. bootstrap base runtime requirements
3. deploy shared services or connect to existing shared services
4. deploy project runtime services
5. publish routes
6. generate wiki pages and operational context

Projects remain separate repos. Cortex Governor remains the platform repo.

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
