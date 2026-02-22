# Wiki Compose Bundle

This bundle builds and serves the MkDocs site for hosted access on `cortex-control`.

## Services

- `wiki-build`: one-shot build job that renders docs into the named volume `wiki_site`.
- `wiki`: static site serving via `nginx:alpine` from `wiki_site`.
- `wiki-proxy`: `caddy:2-alpine` reverse proxy on host port `8085` forwarding to `wiki:80`.

## Usage

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml up --build
```

Rebuild site content:

```bash
docker compose -f bootstrap/compose/wiki/docker-compose.yml run --rm wiki-build
docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d wiki wiki-proxy
```
