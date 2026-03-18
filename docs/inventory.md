# Inventory

Generated from machine-readable Governor sources.
Edit the host catalog, IaC artifacts, ports registry, or project manifests and rerun `make inventory` instead of editing this page directly.

Generated: 2026-03-18 00:10 (local)

## Host Summary

| Host | Role | Address | Management | IaC Status | Declared Ports | Project Assignments |
| --- | --- | --- | --- | --- | ---: | ---: |
| `cortex-control` | shared control plane | `192.168.1.103` | `opentofu-proxmox` | `applied` | 8 | 1 |
| `cortex-data` | shared stateful services host | `<unknown>` | `opentofu-proxmox` | `declared` | 3 | 1 |
| `majelis` | operator and development workstation | `192.168.1.124` | `manual-bootstrap` | `external` | 2 | 0 |

## Host Details

### `cortex-control`

- Role: shared control plane
- Address: `192.168.1.103`
- Management: `opentofu-proxmox`
- IaC status: `applied` via `terraform.tfstate`
- IaC artifact: `infra/proxmox/cortex-control/terraform.tfstate`
- VM name: `cortex-control`
- VMID: `220`
- Notes: Hosted wiki, ingress, monitoring, and platform control services.

### `cortex-data`

- Role: shared stateful services host
- Address: `<unknown>`
- Management: `opentofu-proxmox`
- IaC status: `declared` via `variables.tf`
- IaC artifact: `infra/proxmox/cortex-data/variables.tf`
- VM name: `cortex-data`
- VMID: `<unknown>`
- Notes: Shared Postgres, Redis, MinIO, Vaultwarden, and other data services.

### `majelis`

- Role: operator and development workstation
- Address: `192.168.1.124`
- Management: `manual-bootstrap`
- IaC status: `external` via `<none>`
- IaC artifact: `<none>`
- VM name: `majelis`
- VMID: `<unknown>`
- Notes: Canonical development and Git authority for Cortex Governor.

## Declared Ports By Host

### `cortex-control`

| Port | Proto | Service | Notes |
| ---: | --- | --- | --- |
| 80 | `tcp` | `ingress-http` | Standard web |
| 443 | `tcp` | `ingress-https` | Standard TLS web |
| 3001 | `tcp` | `uptime-kuma` | Live service health dashboard UI |
| 6379 | `tcp` | `redis-cache` | Optional cache/message bus |
| 8080 | `tcp` | `app-http-alt` | Alternate HTTP app port |
| 8085 | `tcp` | `cortex-wiki` | Hosted MkDocs wiki reverse proxy |
| 8443 | `tcp` | `admin-https-alt` | Alternate secure admin UI |
| 9090 | `tcp` | `metrics-ui` | Prometheus-style UI |

### `cortex-data`

| Port | Proto | Service | Notes |
| ---: | --- | --- | --- |
| 5432 | `tcp` | `postgres` | Primary database |
| 9000 | `tcp` | `minio-api` | MinIO API endpoint |
| 9001 | `tcp` | `minio-console` | MinIO Console UI |

### `majelis`

| Port | Proto | Service | Notes |
| ---: | --- | --- | --- |
| 3000 | `tcp` | `ui-dev-server` | Local frontend development |
| 8000 | `tcp` | `docs-dev-server` | Local docs development |

## Project Targets

| Project | Environment | Runtime Host | Ingress Host | Data Host | Manifest |
| --- | --- | --- | --- | --- | --- |
| `sample-app` | `dev` | `sample-app-dev` | `cortex-control` | `cortex-data` | `projects/examples/sample-app.json` |

## Public Routes

| Host | Project | Environment | Service | Port | Runtime Host | Ingress Host |
| --- | --- | --- | --- | ---: | --- | --- |
| `api.sample-app.thecortexstack.com` | `sample-app` | `dev` | `backend` | 8000 | `sample-app-dev` | `cortex-control` |
| `app.sample-app.thecortexstack.com` | `sample-app` | `dev` | `frontend` | 3000 | `sample-app-dev` | `cortex-control` |

## Endpoints

- `http://cortex-control:3001` - Uptime Kuma dashboard
- `http://cortex-control:8085` - hosted Governor wiki
- `http://majelis:3000` - local UI development server
- `http://majelis:8000` - local docs development server
- `https://api.sample-app.thecortexstack.com` - `sample-app` public route for `backend`
- `https://app.sample-app.thecortexstack.com` - `sample-app` public route for `frontend`

## Source Of Truth Links

- Host catalog: `ops/inventory/host-catalog.json`
- Ports registry: `docs/runbooks/ports-registry.yaml`
- Project manifests: `projects/**/*.json`
- IaC directories:
  - `infra/proxmox/cortex-control/`
  - `infra/proxmox/cortex-data/`
