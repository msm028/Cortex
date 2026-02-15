# Edge / Ingress Compose Stack

This stack provides Cloudflare Tunnel ingress and Caddy routing for internal Cortex services.

No host ports are exposed by default (`ports:` is intentionally omitted).

Required environment variable names:

- `TUNNEL_TOKEN`
- `PUBLIC_DOMAIN`

Cloudflare Access policies should protect each exposed hostname in Cloudflare Zero Trust.

Expected routed hostnames:

- `vault.{PUBLIC_DOMAIN}` -> `vaultwarden:80`
- `minio.{PUBLIC_DOMAIN}` -> `minio:9000`
