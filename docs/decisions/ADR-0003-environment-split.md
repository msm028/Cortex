# ADR-0003: Environment Split

## Status

Accepted

## Context

Cortex components currently span development workflows, control-plane services, and stateful data services. We need a clear placement model to reduce coupling, improve operational safety, and keep secret-bearing workloads isolated.

## Decision

Environment responsibilities are split as follows:

- `Majelis`: builder/dev workstation only. No persistent state.
- `cortex-control`: control plane services (MCP, orchestrator, hosted wiki, code-server).
- `cortex-data`: state and secrets (Postgres, MinIO, Vaultwarden).

Skills are script-first and runnable from any host, but MCP exposure is allowed only on `cortex-control`.

## Consequences

- Stateful workloads and secrets are isolated from dev workstation concerns.
- Control-plane access points are centralized.
- Skills remain portable while hosted capability exposure is constrained to a single tier.

## Notes

- Do not place secrets or tokens in ADRs, runbooks, or repository docs.
