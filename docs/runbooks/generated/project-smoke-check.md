# Project Smoke Check Contract

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not execute live health checks, hit live routes, or change deployment state.
Use it as a deterministic first-deployment checklist for what operators should verify after rollout.

## Summary

| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Routes | Operator Checks | Path |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | 3 | 5 | 2 | 4 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`
- Runtime host: `sample-app-dev`
- Ingress dependency: `cortex-control`
- Data dependency: `cortex-data`

### Runtime Services To Verify

| Service | Type | Planned Ports | Planned Verification |
| --- | --- | --- | --- |
| `backend` | `fastapi` | `8000` | Confirm `backend` is visible on `sample-app-dev` and listening on `8000`. |
| `frontend` | `nextjs` | `3000` | Confirm `frontend` is visible on `sample-app-dev` and listening on `3000`. |
| `workers` | `celery` | `<none>` | Confirm `workers` stays running on `sample-app-dev` and shows no immediate startup failures. |

### Routes To Verify

| Host | Service | Port | Upstream | Planned Verification |
| --- | --- | ---: | --- | --- |
| `api.sample-app.thecortexstack.com` | `backend` | 8000 | `sample-app-dev:8000` | Confirm operators can observe the expected response for `api.sample-app.thecortexstack.com` through ingress `cortex-control` after deployment. |
| `app.sample-app.thecortexstack.com` | `frontend` | 3000 | `sample-app-dev:3000` | Confirm operators can observe the expected response for `app.sample-app.thecortexstack.com` through ingress `cortex-control` after deployment. |

### Shared Dependencies To Verify

| Dependency | Type | Host | Planned Verification |
| --- | --- | --- | --- |
| `langfuse` | `langfuse` | `cortex-data` | Confirm `langfuse` remains reachable from `sample-app-dev` on `cortex-data`. |
| `litellm` | `litellm` | `cortex-data` | Confirm `litellm` remains reachable from `sample-app-dev` on `cortex-data`. |
| `otel` | `otel` | `cortex-data` | Confirm `otel` remains reachable from `sample-app-dev` on `cortex-data`. |
| `postgres` | `postgres` | `cortex-data` | Confirm `postgres` remains reachable from `sample-app-dev` on `cortex-data`. Required platform notes: `pgvector`. |
| `redis` | `redis` | `cortex-data` | Confirm `redis` remains reachable from `sample-app-dev` on `cortex-data`. |

### Operator-Visible Checks

- [ ] Runtime services: Confirm runtime host `sample-app-dev` shows the planned workloads running: `backend`, `frontend`, `workers`.
- [ ] Routes: Confirm ingress `cortex-control` presents the documented public routes after deployment: `api.sample-app.thecortexstack.com` -> `sample-app-dev:8000` via `backend`; `app.sample-app.thecortexstack.com` -> `sample-app-dev:3000` via `frontend`.
- [ ] Shared dependencies: Confirm runtime services can reach shared dependencies on `cortex-data`: `langfuse`, `litellm`, `otel`, `postgres`, `redis`.
- [ ] Operator notes: Capture observed results, regressions, and follow-up actions outside this generated artifact before any further rollout work.
