# Project Runtime Skeleton

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not create compose bundles, deploy containers, or change live routing.

## Summary

| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Secrets | Path |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | 3 | 5 | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`

### Host Placement

| Role | Host |
| --- | --- |
| Runtime | `sample-app-dev` |
| Ingress Dependency | `cortex-control` |
| Data Dependency | `cortex-data` |

### Runtime Services

| Service | Type | Exposed Ports | Shared Attachments |
| --- | --- | --- | --- |
| `backend` | `fastapi` | `8000` | `langfuse`, `litellm`, `otel`, `postgres`, `redis` |
| `frontend` | `nextjs` | `3000` | `langfuse`, `litellm`, `otel`, `postgres`, `redis` |
| `workers` | `celery` | `<none>` | `langfuse`, `litellm`, `otel`, `postgres`, `redis` |

### Shared Dependency Attachments

| Dependency | Type | Host | Notes |
| --- | --- | --- | --- |
| `langfuse` | `langfuse` | `cortex-data` | `shared service` |
| `litellm` | `litellm` | `cortex-data` | `shared service` |
| `otel` | `otel` | `cortex-data` | `shared service` |
| `postgres` | `postgres` | `cortex-data` | extensions: `pgvector` |
| `redis` | `redis` | `cortex-data` | `shared service` |

### Planning Skeleton

```yaml
services:
  backend:
    image: ghcr.io/example/sample-app/backend:dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      PROJECT_KEY: sample-app
      PROJECT_ENV: dev
      LANGFUSE_ATTACHMENT: from-cortex-data
      LITELLM_ATTACHMENT: from-cortex-data
      OTEL_ATTACHMENT: from-cortex-data
      POSTGRES_ATTACHMENT: from-cortex-data
      REDIS_ATTACHMENT: from-cortex-data
    expose:
      - "8000"
    labels:
      route.host: api.sample-app.thecortexstack.com
      route.port: '8000'
    # planning-only skeleton; refine in the project repo or deploy plan before execution
  frontend:
    image: ghcr.io/example/sample-app/frontend:dev
    command: npm run start
    environment:
      PROJECT_KEY: sample-app
      PROJECT_ENV: dev
      LANGFUSE_ATTACHMENT: from-cortex-data
      LITELLM_ATTACHMENT: from-cortex-data
      OTEL_ATTACHMENT: from-cortex-data
      POSTGRES_ATTACHMENT: from-cortex-data
      REDIS_ATTACHMENT: from-cortex-data
    expose:
      - "3000"
    labels:
      route.host: app.sample-app.thecortexstack.com
      route.port: '3000'
    # planning-only skeleton; refine in the project repo or deploy plan before execution
  workers:
    image: ghcr.io/example/sample-app/workers:dev
    command: celery -A app.worker worker --loglevel=info
    environment:
      PROJECT_KEY: sample-app
      PROJECT_ENV: dev
      LANGFUSE_ATTACHMENT: from-cortex-data
      LITELLM_ATTACHMENT: from-cortex-data
      OTEL_ATTACHMENT: from-cortex-data
      POSTGRES_ATTACHMENT: from-cortex-data
      REDIS_ATTACHMENT: from-cortex-data
    # planning-only skeleton; refine in the project repo or deploy plan before execution
```

### Secret References

- `sample-app-dev-db`
- `sample-app-dev-runtime`

### Operator Notes

- Runtime skeleton host: `sample-app-dev`
- Shared dependencies stay off-host and should already exist on `cortex-data`.
- Treat the YAML block above as a planning scaffold only. Final runtime definitions should live in project-specific deployment assets.
