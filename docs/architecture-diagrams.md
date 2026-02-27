# Architecture Diagrams

## As-Built (Current)

```mermaid
flowchart LR
  user["User Browser or Admin"]
  cfedge["Cloudflare Edge"]
  cftun["Cloudflare Tunnel"]

  subgraph majelis["Majelis 192.168.1.124"]
    caddy["edge-caddy-1 ports 80 443 2019"]
    cfagent["edge-cloudflared-1 outbound"]
    vw["core-vaultwarden-1 port 80"]
    minio["core-minio-1 ports 9000 and 9001"]
    pg["core-postgres-1 port 5432"]
    cmf["caddymanager-frontend port 8086"]
    cmb["caddymanager-backend port 3000"]
  end

  subgraph control["cortex-control 192.168.1.103"]
    wiki["wiki-proxy port 8085"]
    caddy2["edge-caddy-1 ports 80 443 2019"]
  end

  user --> cfedge
  cfedge --> cftun
  cftun --> cfagent
  cfagent --> caddy
  caddy --> vw
  caddy --> minio

  user --> wiki
  user --> cmf
  cmf --> cmb
  cmb --> caddy
  user --> pg
  user --> caddy2
```

## Future State (Target)

```mermaid
flowchart LR
  user["User Browser or Operator"]
  cfa["Cloudflare Access Policies"]
  cfedge2["Cloudflare Edge and DNS"]

  subgraph edge["Edge Layer"]
    tunnel["cloudflared outbound"]
    rp["Caddy ingress ports 80 443 2019"]
  end

  subgraph ctrl["cortex-control"]
    wiki2["Hosted Wiki port 8085"]
    mcp["MCP and Orchestrator"]
    codesrv["code-server"]
  end

  subgraph data["cortex-data"]
    vw2["Vaultwarden port 80"]
    minio2["MinIO ports 9000 and 9001"]
    pg2["Postgres port 5432"]
    restic["Restic snapshots in MinIO"]
  end

  subgraph ws["majelis workstation"]
    tools["skills make plan runner and Caddy Manager"]
  end

  user --> cfedge2
  cfedge2 --> cfa
  cfa --> tunnel
  tunnel --> rp
  rp --> vw2
  rp --> minio2
  rp --> wiki2
  mcp --> vw2
  mcp --> pg2
  mcp --> minio2
  restic --> minio2
  tools --> mcp
  tools --> ctrl
  tools --> data
  tools --> rp
```

## Notes

- As-built diagram reflects the current active deployment pattern observed in February 2026.
- Future-state diagram reflects the planned control/data split documented in ADR-0003.
