# Project Env Contract

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not resolve Vaultwarden items, inject env values, or deploy services.

## Summary

| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Vaultwarden Refs | Path |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | 3 | 5 | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`
- Runtime host: `sample-app-dev`
- Data dependency host: `cortex-data`

### Vaultwarden Reference Set

- `sample-app-dev-db`
- `sample-app-dev-runtime`

### Shared Dependency Contract

| Dependency | Type | Attachment Var | Non-Secret Env Vars | Secret Env Vars | Vaultwarden Refs | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `langfuse` | `langfuse` | `LANGFUSE_ATTACHMENT` | `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY` | `LANGFUSE_SECRET_KEY` | `sample-app-dev-db`, `sample-app-dev-runtime` | Expose the shared Langfuse endpoint and keep any secret key retrieval outside the repo. |
| `litellm` | `litellm` | `LITELLM_ATTACHMENT` | `LITELLM_BASE_URL` | `<none>` | `<none>` | Point clients at the shared LiteLLM gateway on the data host. |
| `otel` | `otel` | `OTEL_ATTACHMENT` | `OTEL_EXPORTER_OTLP_ENDPOINT` | `<none>` | `<none>` | Use the shared OTLP collector endpoint for traces, logs, or metrics. |
| `postgres` | `postgres` | `POSTGRES_ATTACHMENT` | `POSTGRES_HOST`, `POSTGRES_PORT` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` | `sample-app-dev-db`, `sample-app-dev-runtime` | Prefer resolving database credentials or a composed connection string from Vaultwarden at runtime. |
| `redis` | `redis` | `REDIS_ATTACHMENT` | `REDIS_HOST`, `REDIS_PORT` | `REDIS_URL` | `sample-app-dev-db`, `sample-app-dev-runtime` | Keep any Redis auth or database-selection details in Vaultwarden-backed runtime config. |

### Runtime Service Contract

| Service | Type | Expected Env Vars | Shared Attachment Vars | Vaultwarden Usage |
| --- | --- | --- | --- | --- |
| `backend` | `fastapi` | `PROJECT_KEY`, `PROJECT_ENV`, `PORT`, `PUBLIC_ROUTE_HOSTS`, `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | manual retrieval for `sample-app-dev-db`, `sample-app-dev-runtime` |
| `frontend` | `nextjs` | `PROJECT_KEY`, `PROJECT_ENV`, `PORT`, `PUBLIC_ROUTE_HOSTS`, `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | manual retrieval for `sample-app-dev-db`, `sample-app-dev-runtime` |
| `workers` | `celery` | `PROJECT_KEY`, `PROJECT_ENV`, `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT` | manual retrieval for `sample-app-dev-db`, `sample-app-dev-runtime` |

### Planning Notes

- Attachment vars above are deterministic planning placeholders only; bind concrete values in project-specific runtime assets later.
- Secret values are intentionally omitted. Resolve only the listed Vaultwarden references during manual planning or future runtime implementation.
- Use the shared dependency rows to translate attachment placeholders into concrete runtime vars such as `DATABASE_URL`, `REDIS_URL`, or `OTEL_EXPORTER_OTLP_ENDPOINT`.
