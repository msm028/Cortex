# Wiki Reorganization Plan

## Purpose

Reshape the Cortex Governor wiki into a smaller, clearer operator manual that matches the current platform direction:

- Cortex Governor is the infrastructure and auto-wiki product
- project application code lives outside this repo
- docs should separate stable operator knowledge from generated reference and legacy material

## Why Reorganize

The current wiki has grown in layers:

- legacy homelab bootstrap material
- current control-plane runbooks
- generated project artifacts
- live status/reference pages
- new platform-model documentation

That creates three problems:

1. navigation mixes stable runbooks, generated pages, and transitional notes
2. architecture and process diagrams do not give one clean mental model
3. operator-facing pages and implementation-history pages are too close together

## Reorganization Goals

The revised wiki should make it easy to answer five questions:

1. What is Cortex Governor?
2. How is Cortex Governor structured?
3. How do I operate Cortex Governor safely?
4. How does a new project use Cortex Governor?
5. Where do I find generated status and reference material?

## Target Information Architecture

### 1. Overview

Purpose: orient readers quickly.

Keep or rewrite here:

- `index.md`
- `ARCHITECTURE.md`
- `architecture-system-map.md`
- `process-flow.md`
- `wiki-reorganization-plan.md`

### 2. Operate Cortex Governor

Purpose: daily operator workflows and platform controls.

Keep or rewrite here:

- `runbooks/how-to-use-cortex.md`
- `runbooks/git-and-host-management.md`
- `runbooks/ops-commands.md`
- `runbooks/agent-loop.md`
- `runbooks/plans.md`
- `runbooks/doctor.md`
- `runbooks/smoke.md`
- `runbooks/bw-cli.md`
- `runbooks/vaultwarden-env.md`

### 3. Provisioning

Purpose: create and maintain infrastructure targets.

Keep or rewrite here:

- `runbooks/provisioning-iac.md`
- `runbooks/provision-cortex-control.md`
- `runbooks/provision-cortex-data.md`

Future additions belong here:

- project runtime host provisioning
- manifest-driven IaC generation

### 4. Services

Purpose: run shared services that Cortex owns.

Keep or rewrite here:

- `runbooks/deploy-wiki.md`
- `runbooks/publish-wiki-cloudflare-access.md`
- `runbooks/deploy-uptime-kuma.md`
- `runbooks/hosted-ops-status-refresh.md`
- `runbooks/edge-access.md`
- `runbooks/backups.md`
- `runbooks/vaultwarden.md`

### 5. Projects

Purpose: how external projects integrate with Cortex Governor.

Keep or rewrite here:

- `runbooks/project-platform-model.md`
- `runbooks/project-manifests.md`
- `projects.md`
- generated project artifact pages under `runbooks/generated/`

### 6. Reference

Purpose: generated or lookup-style material.

Keep or rewrite here:

- `inventory.md`
- `ops-status.md`
- `runbooks/env-vars.md`
- `runbooks/ports-and-service-map.md`
- `governance/GOVERNANCE.md`
- `governance/ci.md`
- `decisions/README.md` and ADRs
- `CHANGELOG.md`

### 7. Archive

Purpose: keep historical context without polluting the main navigation.

Archive candidates:

- `runbooks/bootstrap-core.md`
- `runbooks/golden-path.md`
- `runbooks/status.md`
- `runbooks/testing.md`
- current `architecture-diagrams.md` after replacement diagrams are accepted

These pages are not necessarily wrong. They are just not good top-level navigation targets for the current platform direction.

## Page Disposition

| Page Group | Action | Reason |
| --- | --- | --- |
| Home, architecture, usage pages | Rewrite and promote | These define the platform mental model |
| IaC provisioning pages | Keep with light cleanup | They are active and map to real OpenTofu stacks |
| Service runbooks | Keep and group under Services | They remain operationally relevant |
| Project manifest pages | Keep and group under Projects | They are central to the new platform model |
| Generated project artifacts | Keep but subordinate | Useful output, not top-level navigation |
| Inventory and ops status | Keep as Reference | Important, but lookup-oriented |
| Governance and ADRs | Keep as Reference | Stable policy and design record |
| Legacy bootstrap/status/testing pages | Archive | Too transitional or overlapping |

## Fresh Diagram Approach

The current diagram page mixes old topology, target state, and service detail on one screen.

Replace it with two canonical diagram pages:

### 1. System Architecture Diagram

Purpose:

- show host roles
- show control-plane boundaries
- show where ingress, data, and project runtimes belong
- stay stable even when individual services change

Rules:

- one diagram only
- host-role centric
- avoid listing every container
- show control flow and dependency direction, not every port

New canonical page:

- `architecture-system-map.md`

### 2. Process Diagram

Purpose:

- show how Cortex Governor handles a new project
- show approval gates
- show where project manifests, OpenTofu, runtime deployment, and wiki generation fit

Rules:

- workflow centric
- one happy path
- explicit approval gates
- explicit human/apply boundary

New canonical page:

- `process-flow.md`

## Diagram Retirement Plan

1. Add the new canonical system and process diagram pages.
2. Mark `architecture-diagrams.md` as legacy.
3. After the new navigation has been used for a while, move the old page into Archive.

## Recommended Navigation Update

Target top-level nav:

- Home
- Overview
- Operate Cortex Governor
- Provisioning
- Services
- Projects
- Reference
- Decisions
- Archive

This is a better fit than one long `Runbooks` bucket.

## Implementation Order

### Phase 1: Navigation Cleanup

- rewrite home page
- add canonical system and process diagram pages
- add this reorganization plan
- mark legacy diagram page as transitional

### Phase 2: Content Grouping

- regroup active runbooks under Operate, Provisioning, Services, Projects, Reference
- demote generated project pages in nav
- move noisy transitional pages toward Archive

### Phase 3: Generated Reference Improvement

- make `inventory.md` generated from IaC outputs plus project/runtime facts
- keep `ops-status.md` generated
- distinguish generated reference from hand-written runbooks clearly

### Phase 4: Archive Pass

- move non-core legacy pages into Archive
- add one archive index with short explanations for why pages were moved

## Success Criteria

The wiki reorganization is successful when:

- a new operator can understand Cortex Governor from the first three pages
- the diagram set is understandable without reading implementation history
- runbooks reflect active workflows rather than old bootstrap history
- generated pages are clearly marked as generated reference
- project onboarding has a clear path from manifest to deployment workflow
