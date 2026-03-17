# Cortex Governor Project Platform Model

## Purpose

Define how new projects will use Cortex Governor without being absorbed into the Cortex Governor repository.

The operating model is:

- Cortex Governor is the platform repo
- each product or application stays in its own repo
- Cortex Governor provisions, deploys, routes, documents, and audits the infrastructure those projects need

## Scope Boundary

### Cortex Governor Owns

- VM and host provisioning
- base OS bootstrap
- Docker and runtime installation
- shared data and platform services
- ingress and reverse proxy configuration
- deployment plans, approvals, and audits
- generated wiki pages, runbooks, inventory, and status

### Project Repos Own

- application source code
- application tests
- product-specific business logic
- app build artifacts and release semantics
- project-local environment defaults that are not shared platform concerns

## Target Host Roles

- `majelis`: operator and development workstation where plans are created and validated
- `cortex-control`: shared control plane for wiki, ingress, monitoring, and platform control services
- `cortex-data`: shared stateful services such as Postgres, pgvector, Redis, MinIO, and Vaultwarden
- project runtime host(s): application-specific deployment targets for frontend, backend, and workers

Do not treat `cortex-control` as the default development box. Keep it stable as the platform control plane.

## Initial Shared Platform Services

The initial reusable platform catalog should support:

- PostgreSQL
- pgvector
- Redis
- MinIO
- Vaultwarden
- LiteLLM
- Langfuse
- OpenTelemetry Collector
- Caddy ingress and route publication

For the first MVP projects, application runtimes should remain separate from the control plane:

- Next.js frontend
- FastAPI backend
- Celery workers

## Project Infrastructure Contract

Each new project should provide a machine-readable manifest. The canonical repo format is JSON so Cortex Governor can validate it deterministically without extra parser dependencies.

The initial shape should cover these fields:

```json
{
  "schema_version": 1,
  "project": {
    "key": "sample-app",
    "name": "Sample App",
    "environment": "dev"
  },
  "targets": {
    "runtime_host": "sample-app-dev",
    "ingress_host": "cortex-control",
    "data_host": "cortex-data"
  },
  "domains": {
    "public": ["app.example.com", "api.example.com"]
  },
  "services": {
    "frontend": { "type": "nextjs", "enabled": true },
    "backend": { "type": "fastapi", "enabled": true },
    "workers": { "type": "celery", "enabled": true },
    "postgres": { "enabled": true, "shared": true, "extensions": ["pgvector"] },
    "redis": { "enabled": true, "shared": true },
    "litellm": { "enabled": true, "shared": true },
    "langfuse": { "enabled": true, "shared": true },
    "otel": { "enabled": true, "shared": true }
  },
  "routes": [
    { "host": "app.example.com", "service": "frontend", "port": 3000 },
    { "host": "api.example.com", "service": "backend", "port": 8000 }
  ],
  "secrets": {
    "vaultwarden_items": ["sample-app-dev-runtime", "sample-app-dev-db"]
  }
}
```

## What Cortex Governor Should Generate From The Contract

From one project manifest, Cortex should be able to generate:

- VM or host provisioning steps
- bootstrap steps for Docker and dependencies
- compose bundles or deployment artifacts
- reverse proxy route definitions
- env requirement documentation
- Vaultwarden mapping references
- health and smoke plans
- wiki pages for topology, endpoints, and runbooks

## Deployment Lifecycle

Standard lifecycle for a project deployment:

1. validate platform readiness on `majelis`
2. provision or select target VM/host
3. bootstrap base runtime on target
4. deploy shared service dependencies if required
5. deploy project runtime services
6. publish or update reverse proxy routes
7. verify health checks and smoke plans
8. rebuild and publish the wiki

## Direction Change Rationale

This model is a deliberate correction in direction.

We are not building Cortex Governor into the next project. We are building Cortex Governor into the platform that helps launch and operate future projects.

That gives us:

- stronger separation of concerns
- reusable automation
- cleaner documentation
- lower risk when onboarding multiple projects over time

## Near-Term Implementation Priorities

1. stabilize current Cortex Governor services and host-role boundaries
2. provision and operationalize `cortex-data`
3. add first-class platform bundles for Redis and pgvector
4. add first-class platform bundles for LiteLLM, Langfuse, and OpenTelemetry
5. define and validate the first project manifest contract
6. generate wiki pages and route config from that contract
