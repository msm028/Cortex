# Cortex Governor Docs

Cortex Governor is the governed infrastructure control plane for **The Cortex Stacks**.
It provisions and operates shared infrastructure, publishes operator documentation, and manages supervised infrastructure workflows for projects that live outside this repo.

## What This Repo Is For

Use this repo for:

- infrastructure provisioning and host bootstrap
- shared service and ingress operations
- governed plan, validate, approve, execute workflows
- generated operator docs, inventory, and status
- project infrastructure manifests and onboarding artifacts

Do not use this repo for:

- application source code
- product UX or workspace features
- long-lived project-specific business logic

## Start Here

- [Architecture](./ARCHITECTURE.md)
- [System Architecture Diagram](./architecture-system-map.md)
- [Project Onboarding Process](./process-flow.md)
- [How To Use Cortex Governor](./runbooks/how-to-use-cortex.md)
- [Governance](./governance/GOVERNANCE.md)
- [Decisions](./decisions/README.md)
- [Git And Host File Management Policy](./runbooks/git-and-host-management.md)

## Current Operating Model

- `majelis`: canonical development and operator workstation
- `cortex-control`: deployed control-plane host for wiki, ingress, and monitoring
- `cortex-data`: planned shared data/services host
- separate project repos: application code and product logic

## Key Generated Views

- [Inventory](./inventory.md)
- [Ops Status](./ops-status.md)
- [Project Catalog](./projects.md)
- [Project Platform Model](./runbooks/project-platform-model.md)

## Cleanup And Direction

- [Wiki Reorganization Plan](./wiki-reorganization-plan.md)
