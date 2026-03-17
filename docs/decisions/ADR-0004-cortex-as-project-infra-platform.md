# ADR-0004: Cortex As Project Infra Platform

## Status

Accepted

## Context

Cortex started as a bootstrap repository for the homelab control plane and supporting services. As planning moved toward future product work, there was a risk that Cortex would absorb application-specific concerns and turn into a mixed repo containing both platform operations and project runtime assumptions.

That direction would weaken the repository in three ways:

- it would blur the boundary between shared infrastructure and per-project application code
- it would make documentation and automation less reusable across projects
- it would increase change risk by coupling project experimentation to the control plane

We want Cortex to become a reusable infra tool and auto-wiki system that AI can use during development to provision fresh environments, bootstrap shared services, and publish operational context without owning the application repos themselves.

## Decision

Cortex is defined as a generic infrastructure and documentation platform, not an application repository.

Its responsibilities are:

- provision and bootstrap target hosts and VMs
- manage shared platform services and base runtimes
- validate, approve, execute, and audit infrastructure plans
- manage ingress and route publication through the existing reverse proxy layer
- generate and publish operator-facing wiki documentation automatically

Its non-goals are:

- storing application source code for user projects
- embedding project-specific business logic
- hardcoding one project's stack, domains, or runtime settings into the platform

New projects will live in separate repositories and integrate with Cortex through a project infrastructure contract. That contract will describe requested services, routes, secrets references, and deployment targets while keeping Cortex reusable across multiple projects.

## Consequences

- Cortex remains a platform control repo instead of becoming a monolithic app-plus-infra repo.
- Shared services such as ingress, PostgreSQL, pgvector, Redis, LiteLLM, Langfuse, and OpenTelemetry can be offered as reusable capabilities when they become first-class platform modules.
- Each project can evolve its app code independently while still using Cortex for provisioning, deployment workflows, and wiki publication.
- Documentation must distinguish between platform scope and project scope.

## Direction Change

The direction change is intentional:

- before: Cortex risked drifting toward a project-shaped environment
- now: Cortex is explicitly the infra tool that provisions and documents project environments

This keeps control-plane concerns stable while allowing future projects to consume the platform through repeatable manifests, plans, and runbooks.

## Notes

- Existing governance still applies: secret values stay out of Git, plans, logs, and docs.
- Agent autonomy remains constrained by policy; destructive and infrastructure-changing actions continue to require validation and approval rules.
