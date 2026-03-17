# Project Catalog

Generated from machine-readable project manifests under `projects/`.
Edit manifests in `projects/` and rerun `make project-catalog` instead of editing this page directly.

## Summary

| Project | Environment | Runtime Host | Ingress Host | Data Host | Routes | Path |
| --- | --- | --- | --- | --- | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | `cortex-control` | `cortex-data` | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Runtime host: `sample-app-dev`
- Ingress host: `cortex-control`
- Data host: `cortex-data`
- Manifest: `projects/examples/sample-app.json`
- Public domains: `app.sample-app.thecortexstack.com`, `api.sample-app.thecortexstack.com`
- Enabled services: `backend (fastapi)`, `frontend (nextjs)`, `langfuse (langfuse)`, `litellm (litellm)`, `otel (otel)`, `postgres (postgres)`, `redis (redis)`, `workers (celery)`

| Route Host | Service | Port |
| --- | --- | ---: |
| `app.sample-app.thecortexstack.com` | `frontend` | 3000 |
| `api.sample-app.thecortexstack.com` | `backend` | 8000 |
