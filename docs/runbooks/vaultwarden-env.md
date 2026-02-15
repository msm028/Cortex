# Vaultwarden Environment Injection

## Purpose

Load required environment variables from Vaultwarden via Bitwarden CLI without storing secret values in the repository.

## Required Environment Variables (Names Only)

- `PUBLIC_DOMAIN`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `VAULTWARDEN_ADMIN_TOKEN`
- `TUNNEL_TOKEN`

## Install and Session Setup

Install Bitwarden CLI (`bw`), then log in and unlock:

```bash
bw login
bw unlock --raw
```

Export the returned unlock token as `BW_SESSION` in the current shell/session only.

## Mapping File

Populate item IDs in:

- `ops/env/vaultwarden-map.json`

Mapping entries use IDs only and a source selector:

- `login.username`
- `login.password`
- `field:<FieldName>`

Do not place secret values in docs or repository files.

## Usage

Validate mapping/session:

```bash
make vw-check
```

Run bootstrap-check with injected environment values:

```bash
PUBLIC_DOMAIN=thecortexstack.com make vw-bootstrap-check
```

Run an arbitrary command with injected values:

```bash
PUBLIC_DOMAIN=thecortexstack.com make vw-run CMD="make plan TEMPLATE=stack-status ENV=dev"
```

## No Manual Export

Recommended operator sequence:

```bash
export BW_SESSION=<from-bw-unlock-raw>
PUBLIC_DOMAIN=thecortexstack.com make vw-doctor
PUBLIC_DOMAIN=thecortexstack.com make vw-bootstrap-check
```

`vw-run`/`vw-bootstrap-check` inject mapped secret values at execution time, so manual export of those secret variables is not required.

`make up*` will fail until `make env-check` passes; use `make vw-doctor` + `make vw-bootstrap-check`.

## Daily Operator Commands

```bash
PUBLIC_DOMAIN=thecortexstack.com make vw-doctor
PUBLIC_DOMAIN=thecortexstack.com make vw-up
make plan TEMPLATE=stack-status ENV=dev
make plan TEMPLATE=ingress-status ENV=dev
```

## Troubleshooting

- Mapping placeholders:
  - replace `REPLACE_ME` item IDs in `ops/env/vaultwarden-map.json`
- Expired or missing `BW_SESSION`:
  - run `bw unlock --raw` again and export a fresh session
- Missing `bw` CLI:
  - install Bitwarden CLI and ensure `bw` is on `PATH`
