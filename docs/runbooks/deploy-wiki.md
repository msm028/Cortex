# Deploy Wiki

## Purpose

Deploy and operate the hosted MkDocs wiki service on `cortex-control`.

## Compose Bundle

- Compose file: `bootstrap/compose/wiki/docker-compose.yml`
- Proxy config: `bootstrap/compose/wiki/Caddyfile`
- Published endpoint: `http://cortex-control:8085/`

## Deploy

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d --build
```

This starts:
- `wiki-build` to render static docs into the `wiki_site` volume.
- `wiki` (nginx) to serve static files.
- `wiki-proxy` (caddy) to expose the service on port `8085`.

## Update Docs Content

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml run --rm wiki-build
docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d wiki wiki-proxy
```

## Syncing `/opt/cortex`

When updating the deployed checkout itself, prefer the sync wrapper so generated `docs/ops-status.md` changes do not block fast-forwards:

```bash
cd /opt/cortex
ops/bin/sync_deployed_checkout.sh --bundle /tmp/cortex-main-<sha>.bundle --refresh-wiki
```

This keeps the deployment checkout predictable while still publishing fresh ops status in the wiki.

## Verify

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml ps
curl -fsS http://127.0.0.1:8085/ >/dev/null && echo "WIKI: PASS"
```

## Rollback

1. Checkout the previous known-good commit.
2. Rebuild and restart:

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml run --rm wiki-build
docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d wiki wiki-proxy
```
