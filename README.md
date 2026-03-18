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

## Repo Boundary

This repository should stay narrow:

- keep `ops/`, `infra/`, `bootstrap/`, `projects/`, and Governor runbooks here
- keep application code, workspace UX, and product-specific logic out of this repo
- treat generated docs as derived artifacts, not hand-maintained truth

Future products like `Cortex Workbench` should live in separate repositories and integrate with Governor through manifests, plans, and shared service contracts.

## Working Model

- Canonical development checkout: `majelis`
- Deployment checkout: `cortex-control:/opt/cortex`
- Risky or infrastructure-changing actions remain human-in-the-loop

## Current State

Today Cortex Governor is strongest at:

- deterministic validation and plan lifecycle tooling
- hosted wiki, inventory, and ops-status publication
- project manifest validation and generated onboarding artifacts
- controlled deployment-host sync and supervised background work

It is not yet a full end-to-end project runtime deployer.

## Near-Term Direction

The next platform steps are:

- keep the repo aligned around Governor-only scope
- stand up shared platform pieces only when they support more than one workflow
- keep `cortex-control` stable as the control plane
- bring up `cortex-data` when shared stateful services are needed beyond bootstrap convenience

See:

- [Docs Home](./docs/index.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Git And Host File Management Policy](./docs/runbooks/git-and-host-management.md)
