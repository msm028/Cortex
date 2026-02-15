# Bootstrap Core Runbook

## Core Stack

`bootstrap/compose/core/docker-compose.yml` defines the Cortex core bootstrap services:

- `postgres`
- `minio`
- `vaultwarden`

All services are internal-only by default. No host port publishing is defined.

## Pinned Images

Core image tags are intentionally pinned (no `:latest`):

- `postgres:16`
- `minio/minio:RELEASE.2024-10-29T16-01-48Z`
- `vaultwarden/server:1.32.2`

Upgrade procedure:

1. Edit `bootstrap/compose/core/docker-compose.yml` and bump only the intended image tag(s).
2. Run:
   - `make validate`
   - `make test`
3. Submit the tag bump with release notes and rollback notes in the PR description.

## Dry-Run Validation

Use the plan template:

```bash
python3 ops/plan/mkplan.py --template bootstrap-core-dry-run
```

Then validate and execute in default dry-run mode:

```bash
make validate-plan PLAN=plans/<generated>.json
make execute PLAN=plans/<generated>.json
```

Default execution is dry-run, so actions are logged to audit without running infrastructure commands.

## Bring Up

Use controlled plan flow for startup:

1. Generate plan:
   - `python3 ops/plan/mkplan.py --template bootstrap-core-up`
2. Validate plan:
   - `make validate-plan PLAN=plans/<generated>.json`
3. Approve plan (required by command policy):
   - `make approve PLAN=plans/<generated>.json VAULTWARDEN_ITEM_ID=<id>`
4. Execute plan:
   - Dry-run default:
     - `make execute PLAN=plans/<generated>.json`
   - Operator-managed real execution (only after approval):
     - `python3 ops/executor/execute_plan.py --plan plans/<generated>.json --dry-run false --allow-infra-exec true`

The bring-up template performs:

- `docker compose up -d`
- `docker ps` status listing
- deterministic health verification for `postgres`, `minio`, and `vaultwarden`
  - health polling runs every 2 seconds and may take up to 120 seconds before success/timeout

## Rollback

Use rollback plan flow:

1. Generate rollback plan:
   - `python3 ops/plan/mkplan.py --template bootstrap-core-down`
2. Validate and approve:
   - `make validate-plan PLAN=plans/<generated>.json`
   - `make approve PLAN=plans/<generated>.json VAULTWARDEN_ITEM_ID=<id>`
3. Execute:
   - Dry-run default:
     - `make execute PLAN=plans/<generated>.json`
   - Operator-managed real rollback:
     - `python3 ops/executor/execute_plan.py --plan plans/<generated>.json --dry-run false --allow-infra-exec true`

Rollback template performs:

- `docker compose down`
- deterministic verification that core containers are stopped/absent

Ports remain unexposed by default. External access should be added later via Cloudflare/Access or internal networking controls.

## Secrets Handling

Secrets must not be stored in this repository.

- Compose uses environment variable references only.
- Operational references should use Vaultwarden item IDs only.
