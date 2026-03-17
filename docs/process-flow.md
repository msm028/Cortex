# Cortex Governor Project Onboarding Process

This is the canonical process diagram for how Cortex Governor should handle a new project.

It describes the supervised target workflow rather than a one-off historical sequence.

```mermaid
flowchart TB
  start["New project request"]
  manifest["Create or update project manifest"]
  validate["Validate manifest and platform prerequisites"]
  gen["Generate plans, routes, env contract, smoke checks, and wiki artifacts"]
  review{"Human review and approvals needed?"}
  iac["Prepare OpenTofu plan for hosts or VM changes"]
  apply{"Human runs apply?"}
  bootstrap["Bootstrap runtime host and shared dependencies"]
  deploy["Deploy project runtime services"]
  routes["Publish ingress routes"]
  verify["Run smoke checks and health verification"]
  publish["Publish inventory, status, and wiki updates"]
  done["Project ready for operator handoff"]

  start --> manifest
  manifest --> validate
  validate --> gen
  gen --> review
  review -->|No| bootstrap
  review -->|Yes| iac
  iac --> apply
  apply -->|Approved and executed| bootstrap
  apply -->|Not approved| gen
  bootstrap --> deploy
  deploy --> routes
  routes --> verify
  verify --> publish
  publish --> done
```

## Reading Guide

- Cortex Governor prepares and validates as much as possible before risky execution.
- Approval gates sit before destructive or infrastructure-changing steps.
- `apply` remains a human step under current governance.
- Wiki publication is part of the delivery workflow, not an afterthought.

## Current Versus Target

Current Cortex Governor already covers:

- manifest validation
- generated planning artifacts
- operator docs and wiki publication
- supervised queue execution

Target Cortex Governor should additionally cover:

- stronger host bootstrap automation
- project runtime deployment templates
- generated inventory from IaC and runtime facts
