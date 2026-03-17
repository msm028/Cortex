# Project Handoff Packet

Generated from validated project manifests under `projects/`.
Planning only. This artifact does not bootstrap hosts, deploy services, resolve secret values, or execute health checks.
It summarizes the operator-facing planning artifacts that Cortex can already derive from the same validated manifests.

## Summary

| Project | Environment | Runtime Host | Routes | Runtime Services | Shared Dependencies | Vaultwarden Refs | Path |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `sample-app` | `dev` | `sample-app-dev` | 2 | 3 | 5 | 2 | `projects/examples/sample-app.json` |

## Sample App

- Key: `sample-app`
- Environment: `dev`
- Manifest: `projects/examples/sample-app.json`
- Runtime host: `sample-app-dev`
- Ingress dependency: `cortex-control`
- Data dependency: `cortex-data`

### Artifact References

| Artifact | Generated Path | Operator Summary |
| --- | --- | --- |
| Route preview | `docs/runbooks/generated/project-route-preview.md` | 2 route(s): `api.sample-app.thecortexstack.com` -> `sample-app-dev:8000` via `backend`; `app.sample-app.thecortexstack.com` -> `sample-app-dev:3000` via `frontend` |
| Deploy plan | `docs/runbooks/generated/project-deploy-plan.md` | 8 enabled service(s), 2 route(s), 2 Vaultwarden reference(s), 5 operator checkpoint(s). |
| Bootstrap checklist | `docs/runbooks/generated/project-bootstrap-checklist.md` | 6 prerequisite check(s), 3 runtime-host service(s), 5 shared dependency attachment(s), 6 approval checkpoint(s). |
| Runtime skeleton | `docs/runbooks/generated/project-runtime-skeleton.md` | 3 runtime service scaffold(s), 5 shared dependency attachment(s), exposed planning ports `3000`, `8000`. |
| Env contract | `docs/runbooks/generated/project-env-contract.md` | 3 runtime contract(s), 5 shared dependency contract(s), attachment vars `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT`, secret env vars `DATABASE_URL`, `LANGFUSE_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `REDIS_URL`. |
| Smoke-check contract | `docs/runbooks/generated/project-smoke-check.md` | 3 runtime verification target(s), 2 route verification target(s), 5 shared dependency verification target(s), 4 operator-visible check(s). |

### Operator Handoff Checklist

- [ ] Review route preview coverage for ingress `cortex-control` into runtime `sample-app-dev`: `api.sample-app.thecortexstack.com` -> `sample-app-dev:8000` via `backend`; `app.sample-app.thecortexstack.com` -> `sample-app-dev:3000` via `frontend`.
- [ ] Review deployment and bootstrap planning together for `sample-app` before any manual execution work on `sample-app-dev`.
- [ ] Review runtime skeleton and env contract together so attachment placeholders stay aligned: `LANGFUSE_ATTACHMENT`, `LITELLM_ATTACHMENT`, `OTEL_ATTACHMENT`, `POSTGRES_ATTACHMENT`, `REDIS_ATTACHMENT`.
- [ ] Review smoke-check expectations after any future rollout and record outcomes outside this generated packet; planned secret env vars remain documentation-only: `DATABASE_URL`, `LANGFUSE_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `REDIS_URL`.
