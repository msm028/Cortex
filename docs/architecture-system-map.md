# Cortex Governor System Architecture Diagram

This is the canonical high-level system map for Cortex Governor.

It is intentionally role-centric rather than container-centric.

```mermaid
flowchart LR
  operator["Operator or AI agent"]
  browser["User browser"]
  cf["Cloudflare edge and access"]

  subgraph ws["majelis"]
    repo["Cortex Governor repo and runbooks"]
    loop["Agent loop and task queue"]
    plans["Plans validation and docs generation"]
  end

  subgraph control["cortex-control"]
    ingress["Ingress and route publication"]
    wiki["Hosted wiki and status pages"]
    monitor["Monitoring and control services"]
  end

  subgraph data["cortex-data"]
    db["Postgres and future pgvector"]
    obj["MinIO"]
    secrets["Vaultwarden"]
    cache["Redis and other shared state services"]
  end

  subgraph runtime["Project runtime host"]
    frontend["Frontend"]
    backend["Backend API"]
    workers["Workers"]
  end

  operator --> repo
  repo --> loop
  repo --> plans
  plans --> control
  plans --> data
  plans --> runtime

  browser --> cf
  cf --> ingress
  ingress --> wiki
  ingress --> frontend
  ingress --> backend

  backend --> db
  backend --> obj
  backend --> cache
  workers --> db
  workers --> obj
  workers --> cache
  control --> secrets
  control --> wiki
```

## Reading Guide

- `majelis` is the operator and development workstation.
- `cortex-control` is the control plane for ingress, wiki, and monitoring.
- `cortex-data` is the shared state and secret-bearing host.
- project runtime hosts are where application services should run.

## Scope Notes

- This diagram shows the intended stable platform model.
- It does not try to show every current container.
- Project-specific apps should not be added to the control-plane box by default.
