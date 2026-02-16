# Backups And Restore Test Runbook

## Scope

Core backup captures Docker named volumes from:

- `postgres_data`
- `minio_data`
- `vaultwarden_data`

Backups are written with Restic to MinIO bucket `cortex-restic` at:

- `s3:http://minio:9000/cortex-restic`

## Generate Plans

Generate deterministic plan files:

- `make backup-core`
- `make restore-test`

Each command writes:

- `plans/<name>.json`
- `plans/<name>.json.sha256`

## Execute Backup

1. Generate plan:
   - `make backup-core`
2. Validate and approve:
   - `make validate-plan PLAN=plans/<backup-plan>.json`
   - `make approve PLAN=plans/<backup-plan>.json VAULTWARDEN_ITEM_ID=<id>`
3. Execute with Vaultwarden-injected env:
   - `make vw-run CMD="python3 ops/executor/execute_plan.py --plan plans/<backup-plan>.json --dry-run false --allow-infra-exec true"`

Expected action behavior:

- Detects core compose file path.
- Detects active core Docker network from running core containers.
- Creates MinIO bucket `cortex-restic` (idempotent).
- Keeps `minio` running (it hosts the Restic repository).
- Stops `postgres` and `vaultwarden` for snapshot consistency.
- Checks that `core-minio-1` is available before running Restic backup.
- Runs Restic backup from mounted read-only volumes under `/src`.
- Starts `postgres` and `vaultwarden` again with compose `up -d`.
- Prints one summary line: `BACKUP-CORE: PASS` or `BACKUP-CORE: FAIL`.

## Execute Restore Test

1. Generate plan:
   - `make restore-test`
2. Validate and approve if required by policy:
   - `make validate-plan PLAN=plans/<restore-plan>.json`
3. Execute with Vaultwarden-injected env:
   - `make vw-run CMD="python3 ops/executor/execute_plan.py --plan plans/<restore-plan>.json --dry-run false --allow-infra-exec true"`

Restore test behavior:

- Restores latest Restic snapshot into `artifacts/restore-test/<timestamp>/`.
- Verifies:
  - Vaultwarden `db.sqlite3` exists.
  - Postgres `PG_VERSION` exists.
  - MinIO restore path is non-empty.
- Prints one summary line: `RESTORE-TEST: PASS` or `RESTORE-TEST: FAIL`.

## Artifacts

- Plan execution audit logs:
  - `artifacts/audit/*.audit.json`
- Restore-test output tree:
  - `artifacts/restore-test/<timestamp>/`

## Consistency Notes

- Postgres and Vaultwarden are captured while stopped.
- MinIO remains online so Restic can write to `cortex-restic`; MinIO volume data is captured from a live read-only mount and may reflect in-flight object-store changes during backup.

## Troubleshooting

- `BW_SESSION is not set`:
  - Run `bw unlock --raw` and export `BW_SESSION`, then retry.
- Missing env for backup/restore execution:
  - Ensure `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, and `RESTIC_PASSWORD` are provided through `make vw-run`.
- MinIO not reachable in container network:
  - Verify core stack is running and `core-minio-1` is present on Docker.
- Restic repository issues:
  - Confirm MinIO bucket access and credentials, then rerun backup to initialize if needed.
