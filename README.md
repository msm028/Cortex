# Cortex Governor

[![CI Smoke (make smoke)](https://github.com/msm028/Cortex/actions/workflows/ci-smoke.yml/badge.svg)](https://github.com/msm028/Cortex/actions/workflows/ci-smoke.yml)

Cortex Governor is the governed infrastructure control plane for **The Cortex Stacks**.

It owns:

- infrastructure provisioning and bootstrap workflows
- plan, validate, approve, execute, and audit controls
- shared service runbooks and deployment guidance
- project infrastructure manifests and generated onboarding artifacts
- hosted operator wiki, inventory, and status publishing

It does **not** own:

- application source code for family products
- product-specific business logic
- long-term workspace, promptops, or context application UX

## Current Role In The Family

Within **The Cortex Stacks** family:

- `Cortex Governor` is the infrastructure and governance product
- future products like `Cortex Workbench` should live in separate repositories
- project applications should integrate with Governor through manifests, plans, and shared service contracts

## Working Model

- Canonical development checkout: `majelis`
- Deployment checkout: `cortex-control:/opt/cortex`
- Risky or infrastructure-changing actions remain human-in-the-loop

See:

- [Docs Home](./docs/index.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Git And Host File Management Policy](./docs/runbooks/git-and-host-management.md)
