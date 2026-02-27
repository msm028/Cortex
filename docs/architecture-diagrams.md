# Architecture Diagrams

## As-Built (Current)

```mermaid
flowchart LR
  user[User Browser / Admin]
  cfedge[Cloudflare Edge]
  cftun[Cloudflare Tunnel UUID]

  subgraph majelis[Majelis 192.168.1.124]
    caddy[edge-caddy-1\n:80,:443,:2019]
    cfagent[edge-cloudflared-1\noutbound-only]
    vw[core-vaultwarden-1\n:80]
    minio[core-minio-1\n:9000 API / :9001 Console]
    pg[core-postgres-1\n:5432]
    cmf[caddymanager-frontend\n:8086]
    cmb[caddymanager-backend\n:3000]
  end

  subgraph control[cortex-control 192.168.1.103]
    wiki[wiki-proxy\n:8085]
    caddy2[edge-caddy-1\n:80,:443,:2019]
  end

  user -->|vault.thecortexstack.com| cfedge
  cfedge --> cftun --> cfagent -->|HTTP origin 192.168.1.124:80| caddy
  caddy -->|Host: vault.thecortexstack.com| vw
  caddy -->|Host: minio.thecortexstack.com| minio

  user -->|LAN http://192.168.1.103:8085| wiki
  user -->|LAN http://192.168.1.124:8086| cmf
  cmf -->|/api/*| cmb
  cmb -->|http://host.docker.internal:2019/config| caddy
  user -->|Ops http://192.168.1.124:2019/config| caddy
  user -->|Ops docker| pg
  user -->|Ops docker| caddy2
```

## Future State (Target)

```mermaid
flowchart LR
  user[User Browser / Operator]
  cfa[Cloudflare Access Policies]
  cfedge2[Cloudflare Edge + DNS]

  subgraph edge[Edge Layer]
    tunnel[cloudflared\noutbound-only]
    rp[Caddy ingress\n:80,:443,:2019]
  end

  subgraph ctrl[cortex-control]
    wiki2[Hosted Wiki\n:8085]
    mcp[MCP / Orchestrator\ninternal API]
    codesrv[code-server\ninternal]
  end

  subgraph data[cortex-data]
    vw2[Vaultwarden\n:80]
    minio2[MinIO\n:9000/:9001]
    pg2[Postgres\n:5432]
    restic[Restic snapshots in MinIO bucket]
  end

  subgraph ws[majelis workstation]
    tools[skills + make + plan runner + Caddy Manager]
  end

  user --> cfedge2 --> cfa --> tunnel --> rp
  rp -->|vault.thecortexstack.com| vw2
  rp -->|minio.thecortexstack.com| minio2
  rp -->|wiki.thecortexstack.com| wiki2
  mcp --> vw2
  mcp --> pg2
  mcp --> minio2
  restic --> minio2
  tools -->|secure ops| mcp
  tools -->|IaC apply tofu| ctrl
  tools -->|IaC apply tofu| data
  tools -->|admin API 2019| rp
```

## Notes

- As-built diagram reflects the current active deployment pattern observed in February 2026.
- Future-state diagram reflects the planned control/data split documented in ADR-0003.
