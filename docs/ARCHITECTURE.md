# ARCHITECTURE

## Purpose
Cortex Governor is a governed Plan → Validate → Execute platform for building and operating infrastructure safely.
Deterministic scripts decide; humans approve destructive and higher-risk actions.

Cortex Governor is an infrastructure and documentation product. It is not the home for application source code belonging to future projects.

## Product Boundary

- Cortex Governor owns provisioning, deployment governance, shared service operations, ingress publication, and operator documentation.
- Cortex Governor does not own product application code, workspace UX, prompt authoring UX, or long-lived context application logic.
- Future products should integrate with Governor through manifests, plans, and shared service contracts instead of being added to this repo.

## Current Operating Model

### Canonical Host Roles

- `majelis`: operator and development workstation where plans, docs, validations, and controlled automation run
- `cortex-control`: shared control plane for ingress, hosted wiki, monitoring, and deployment-host operational tasks
- `cortex-data`: planned shared data/services host for stateful platform services
- project runtime hosts: isolated hosts or VMs for project-specific frontend, backend, and worker services

### Current Practical Responsibilities

- `majelis` remains the single development and Git authority for Governor.
- `/opt/cortex` on `cortex-control` is a deployed checkout only.
- Hosted wiki publication and control-plane services run from `cortex-control`.
- Shared data-plane separation is designed for `cortex-data`, but some bootstrap-era services still reflect earlier consolidation.

### Current Capability Baseline

Cortex Governor currently provides:

- deterministic validation and smoke checks
- governed plan, approve, execute, and audit flow
- project manifest validation and generated onboarding artifacts
- generated inventory, project catalog, and ops-status pages
- hosted wiki publishing and deployment-host sync controls

It does not yet provide fully automated project runtime deployment end to end.

## Current Platform Pattern

### Ingress

Cloudflare Tunnel -> Caddy -> hosted wiki, control-plane endpoints, and future project routes.

### Secrets And Runtime Injection

- secret values stay out of Git, plans, and docs
- Vaultwarden/Bitwarden-backed runtime injection remains the current secrets model
- audit artifacts record execution outcomes, not secret payloads

### Documentation And Control Surface

- `make` entrypoints remain the operator surface
- docs are authoritative
- inventory and project views are generated from tracked sources
- live hosted status is generated on the control-plane host and overlaid into the wiki build without dirtying the deployed checkout

## Target Architecture

### Shared Platform Services

Target shared services managed by Cortex over time:

- ingress and route management through Caddy
- Vaultwarden
- PostgreSQL
- pgvector
- Redis
- MinIO
- LiteLLM
- Langfuse
- OpenTelemetry Collector
- hosted wiki and operational status publishing

### Project Integration Model

Each project should provide a machine-readable infrastructure contract, then Cortex should:

1. provision or select runtime targets
2. bootstrap base runtime requirements
3. deploy shared services or connect to existing shared services
4. deploy project runtime services
5. publish routes
6. generate wiki pages and operational context

Projects remain separate repos. Cortex Governor remains the platform repo.

## When `cortex-data` Becomes Worth Standing Up

Stand up `cortex-data` when at least one of these becomes true:

- you want shared Postgres/Redis/MinIO/Vaultwarden off the control plane
- more than one project needs shared stateful services
- Workbench development needs stable shared data services rather than local bootstrap-only services
- you want backup/restore and service placement to match the target architecture instead of the bootstrap-era compromise

If Workbench development starts as mostly UI, API, and workflow work, `cortex-data` is useful but not mandatory on day one.
If Workbench will immediately depend on shared Postgres, pgvector, Redis, or LiteLLM/Langfuse/OTEL, bringing up `cortex-data` earlier is the cleaner path.
