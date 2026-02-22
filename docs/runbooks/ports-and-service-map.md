# Ports And Service Map

## Purpose

Prevent port clashes before starting services by keeping a shared map of commonly used ports.

## Port Map

| Port | Protocol | Service/Owner | Where | Notes |
| --- | --- | --- | --- | --- |
| 80 | TCP | HTTP ingress / web frontends | majelis | Often used by reverse proxies. |
| 443 | TCP | HTTPS ingress / TLS termination | majelis | Public-facing TLS endpoint. |
| 8000 | TCP | Docs/dev web servers | majelis | Common conflict with local tooling. |
| 3000 | TCP | UI dev server | majelis | Typical frontend development port. |
| 8080 | TCP | Alternate HTTP app port | majelis | Frequently used by app containers. |
| 9000 | TCP | MinIO API / admin tooling | cortex-data | Object storage API endpoint. |
| 9001 | TCP | MinIO Console | cortex-data | MinIO web console UI. |
| 9090 | TCP | Metrics/monitoring UI | cortex-control | Common Prometheus-style port. |
| 5432 | TCP | Postgres | cortex-data | Primary relational database port. |
| 6379 | TCP | Redis/cache (if used) | cortex-control | Optional cache/message use. |
| 8443 | TCP | Alternate HTTPS/admin UI | cortex-control | Common secure admin service port. |

## How To Check Before Starting Services

- Standard check:
  - `make skill-ports-check`
- Preflight check (ports + validation):
  - `make preflight`
- Strict mode (fail if any checked port is in use):
  - `make skill-ports-check FAIL=1`
  - `make preflight FAIL=1`
