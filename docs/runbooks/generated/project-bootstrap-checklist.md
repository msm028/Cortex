# Project Bootstrap Checklist

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not bootstrap hosts, create compose files, or change live routing.

## Summary

| Project | Environment | Target Runtime Host | Runtime Services | Shared Dependencies | Routes | Secrets | Path |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | 3 | 5 | 2 | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`

### Target Runtime Host

| Role | Host |
| --- | --- |
| Runtime | `sample-app-dev` |
| Ingress Dependency | `cortex-control` |
| Data Dependency | `cortex-data` |

### Required Runtime Prerequisites

- [ ] Confirm runtime host `sample-app-dev` exists and operator SSH/sudo access is ready.
- [ ] Confirm Docker Engine and the Docker Compose plugin are installed on `sample-app-dev`.
- [ ] Confirm `sample-app-dev` has outbound access for image pulls, package retrieval, and operator SSH management.
- [ ] Confirm ingress host `cortex-control` can reach `sample-app-dev` on routed ports `3000`, `8000`.
- [ ] Confirm dependency hosts remain available for this plan: ingress `cortex-control`, data `cortex-data`.
- [ ] Confirm operators can resolve Vaultwarden references before any manual bootstrap work: `sample-app-dev-db`, `sample-app-dev-runtime`.

### Services Requested

| Service | Type | Shared | Placement | Notes |
| --- | --- | --- | --- | --- |
| `backend` | `fastapi` | `no` | `runtime host` | `<none>` |
| `frontend` | `nextjs` | `no` | `runtime host` | `<none>` |
| `langfuse` | `langfuse` | `yes` | `shared dependency` | `<none>` |
| `litellm` | `litellm` | `yes` | `shared dependency` | `<none>` |
| `otel` | `otel` | `yes` | `shared dependency` | `<none>` |
| `postgres` | `postgres` | `yes` | `shared dependency` | extensions: `pgvector` |
| `redis` | `redis` | `yes` | `shared dependency` | `<none>` |
| `workers` | `celery` | `no` | `runtime host` | `<none>` |

### Secret References

- `sample-app-dev-db`
- `sample-app-dev-runtime`

### Route Dependencies

| Public Host | Service | Port | Dependency |
| --- | --- | ---: | --- |
| `api.sample-app.thecortexstack.com` | `backend` | 8000 | `cortex-control -> sample-app-dev:8000` |
| `app.sample-app.thecortexstack.com` | `frontend` | 3000 | `cortex-control -> sample-app-dev:3000` |

### Human Approval Checkpoints

- [ ] Approve `sample-app-dev` as the first single-VM runtime host for `sample-app`.
- [ ] Approve requested runtime-host services: `backend`, `frontend`, `workers`.
- [ ] Approve shared service dependencies that must already exist: `langfuse`, `litellm`, `otel`, `postgres`, `redis`.
- [ ] Approve route dependencies from ingress `cortex-control` into runtime `sample-app-dev` as documented above.
- [ ] Approve Vaultwarden secret references for manual retrieval only: `sample-app-dev-db`, `sample-app-dev-runtime`.
- [ ] Record explicit human approval before any non-dry-run bootstrap or deployment action outside this generated artifact.
