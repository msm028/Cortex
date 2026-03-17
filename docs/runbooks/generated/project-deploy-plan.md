# Project Deployment Plan

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not provision hosts, deploy services, or change live routing.

## Summary

| Project | Environment | Runtime Host | Ingress Host | Data Host | Services | Routes | Secrets | Path |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | `cortex-control` | `cortex-data` | 8 | 2 | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`

### Target Hosts

| Role | Host |
| --- | --- |
| Runtime | `sample-app-dev` |
| Ingress | `cortex-control` |
| Data | `cortex-data` |

### Enabled Services

| Service | Type | Shared | Notes |
| --- | --- | --- | --- |
| `backend` | `fastapi` | `no` | `<none>` |
| `frontend` | `nextjs` | `no` | `<none>` |
| `langfuse` | `langfuse` | `yes` | `<none>` |
| `litellm` | `litellm` | `yes` | `<none>` |
| `otel` | `otel` | `yes` | `<none>` |
| `postgres` | `postgres` | `yes` | extensions: `pgvector` |
| `redis` | `redis` | `yes` | `<none>` |
| `workers` | `celery` | `no` | `<none>` |

### Routes

| Host | Service | Port | Upstream |
| --- | --- | ---: | --- |
| `api.sample-app.thecortexstack.com` | `backend` | 8000 | `sample-app-dev:8000` |
| `app.sample-app.thecortexstack.com` | `frontend` | 3000 | `sample-app-dev:3000` |

### Secrets References

- `sample-app-dev-db`
- `sample-app-dev-runtime`

### Operator Checkpoints

- [ ] Confirm target hosts are ready: runtime `sample-app-dev`, ingress `cortex-control`, data `cortex-data`.
- [ ] Confirm enabled services are intended for this environment: `backend`, `frontend`, `langfuse`, `litellm`, `otel`, `postgres`, `redis`, `workers`.
- [ ] Confirm planned routes match the manifest and remain planning-only: `api.sample-app.thecortexstack.com` -> `sample-app-dev:8000` via `backend`; `app.sample-app.thecortexstack.com` -> `sample-app-dev:3000` via `frontend`.
- [ ] Confirm Vaultwarden references exist before any manual deployment work: `sample-app-dev-db`, `sample-app-dev-runtime`.
- [ ] Record operator approval and any follow-up execution notes outside this generated artifact before taking non-dry-run actions.
