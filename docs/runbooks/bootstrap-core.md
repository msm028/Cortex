# Bootstrap Core Runbook

## Core Stack

`bootstrap/compose/core/docker-compose.yml` defines the Cortex core bootstrap services:

- `postgres`
- `minio`
- `vaultwarden`

All services are internal-only by default. No host port publishing is defined.

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

## Secrets Handling

Secrets must not be stored in this repository.

- Compose uses environment variable references only.
- Operational references should use Vaultwarden item IDs only.
