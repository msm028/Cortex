# How To Use Cortex Governor

This guide explains a practical day-to-day workflow for operating Cortex Governor from `majelis` and keeping documentation and plans in a healthy loop.

The current direction is that Cortex Governor remains the shared infrastructure and documentation product. Future products and apps should live in separate repositories and use Governor for provisioning, deployment workflows, route publication, and wiki generation.

## What Cortex Governor Is Best For

Cortex Governor is strongest when you need:

- Repeatable infrastructure workflows (plan, validate, execute, audit).
- Deterministic checks before changes (`make preflight`, `make validate`).
- Script-first operations with documented runbooks and tracked outcomes.
- Local homelab control-plane/data-plane management with reproducible commands.
- Shared platform services that more than one project can consume.
- Auto-generated wiki documentation for hosts, services, routes, and operator runbooks.

## What Cortex Governor Is Not For

Avoid using Cortex Governor as:

- the application repository for a product
- the place where business logic is developed
- a dumping ground for one-off project-specific runtime assumptions

Use separate project repos for app code, then connect them to Governor through shared infrastructure contracts and deployment workflows.

## Prerequisites

- Repo cloned on `majelis`.
- Docker and Docker Compose working.
- Bitwarden CLI available when running Vaultwarden-backed commands.
- Environment variables exported as required by the target workflow.

Useful checks:

```bash
make preflight
make validate
```

## Core Operating Loop

Use this loop for most changes:

1. Inspect context and current state.
2. Validate before acting.
3. Build or select a plan.
4. Execute with explicit approval.
5. Verify service health.
6. Update docs/changelog.

### 1) Inspect Current State

```bash
make skill-plan-inspect LIST=1 N=10
make skill-ports-check
```

If a specific plan exists:

```bash
make skill-plan-inspect PLAN="plans/plan-YYYYMMDDTHHMMSSZ.json"
```

### 2) Validate First

```bash
make validate
```

For combined preflight + validation:

```bash
make preflight
```

### 3) Build Or Select Plan

Examples:

```bash
PUBLIC_DOMAIN=thecortexstack.com make plan TEMPLATE=backup-core ENV=dev
PUBLIC_DOMAIN=thecortexstack.com make plan TEMPLATE=restore-test ENV=dev
```

### 4) Approve And Execute

Approve structured plan metadata first:

```bash
python3 ops/executor/approve_plan.py --plan plans/plan-YYYYMMDDTHHMMSSZ.json
python3 ops/executor/validate_plan.py --plan plans/plan-YYYYMMDDTHHMMSSZ.json
```

Execute non-dry-run through Vaultwarden injection:

```bash
DRY_RUN=0 PUBLIC_DOMAIN=thecortexstack.com \
make vw-run CMD="python3 ops/executor/execute_plan.py --plan plans/plan-YYYYMMDDTHHMMSSZ.json --dry-run false --allow-infra-exec true"
```

### 5) Verify Health

Use the relevant smoke/status runbooks and health endpoints.

Common checks:

```bash
make doctor
make bootstrap-check
```

For web-routed services, verify through local route or published endpoint with expected host header.

### 6) Close The Loop In Docs

Update changelog and inventory timestamp:

```bash
make skill-update-docs MSG="Describe what changed"
```

Or run the full flywheel loop:

```bash
make run MSG="Change summary" PLAN="plans/plan-YYYYMMDDTHHMMSSZ.json"
```

## Common Best Use Cases

### 1. Safe Infra Change Execution

When changing compose stacks, tunnel publishing, or VM IaC:

- Run `make preflight`.
- Inspect plan risk with `skill-plan-inspect`.
- Execute only approved plans.
- Confirm audit and service health immediately after.

Why this works: it creates an auditable, deterministic trail and prevents ad-hoc drift.

### 2. Backup + Restore Confidence Loop

For stateful services (Postgres, Vaultwarden, MinIO):

- Run `backup-core`.
- Run `restore-test` into artifacts path.
- Review PASS/FAIL and step diagnostics logs.

Why this works: you validate recoverability, not just backup creation.

### 3. Incident Triage And Fast Recovery

For issues like Vaultwarden crashloops or ingress failures:

- Use targeted runbooks (`vaultwarden.md`, `edge-access.md`, `status.md`).
- Confirm root cause with logs and health endpoints.
- Apply minimal, reversible fixes.
- Document the recovery in changelog.

Why this works: lowers MTTR and reduces repeated outage patterns.

### 4. Documentation-Driven Operations

For team continuity and handoff quality:

- Keep architecture, runbooks, and inventory current.
- Use `make docs-build` before publishing changes.
- Link new workflows in runbook index and MkDocs nav.

Why this works: operators can execute from docs without tribal knowledge.

### 5. Proxmox VM Provisioning With OpenTofu

For control/data plane VM lifecycle:

- Use `infra/proxmox/cortex-control` and `infra/proxmox/cortex-data` scaffolds.
- Run `init`, `plan`, inspect plan output, then apply.
- Use rollback (`destroy`) only with explicit confirmation.

Why this works: parameterized IaC reduces manual VM setup variance.

### 6. New Project Platform Onboarding

For a new app or product:

- keep the app code in its own repo
- define the required platform services and routes
- use Cortex Governor to provision hosts, shared services, and ingress
- publish project context into the hosted wiki

Why this works: the platform stays reusable while projects remain isolated from control-plane internals.

## Quick Command Reference

```bash
# Health and validation
make preflight
make validate

# Skills
make skill-plan-inspect
make skill-ports-check
make skill-update-docs MSG="Update note"

# Flywheel wrapper
make run MSG="Operational change"

# Docs
make docs-build
make docs-serve
```

## Related Runbooks

- [Runbooks Index](./README.md)
- [Plan Validate Execute](./plans.md)
- [Backups And Restore Test](./backups.md)
- [Project Platform Model](./project-platform-model.md)
- [Git And Host File Management Policy](./git-and-host-management.md)
- [Vaultwarden Recovery](./vaultwarden.md)
- [Deploy Wiki](./deploy-wiki.md)
- [Provision Cortex-Control](./provision-cortex-control.md)
- [Provision Cortex-Data](./provision-cortex-data.md)
