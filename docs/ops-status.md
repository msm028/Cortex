# Ops Status

Generated: 2026-03-17 20:09 (local)

## Summary

| Item | Value |
| --- | --- |
| Latest plan | `plan-20260222T025510Z.json` |
| Latest audit status | `PASSED` |
| Latest backup status | `PASS` |
| Latest restore-test status | `FAIL` |
| Live health | `UNKNOWN` |
| Agent loop | `IDLE` |

## Latest Plan

- File: `plan-20260222T025510Z.json`
- Path: `plans/plan-20260222T025510Z.json`
- Modified: `2026-02-22 02:55`

## Latest Audit

- File: `plan-20260222T025510Z.json.20260222T025536Z.audit.json`
- Plan: `plans/plan-20260222T025510Z.json`
- Status: `PASSED`
- Executed at: `2026-02-22T02:55:36Z`

## Backup Status

- Latest backup audit: `plan-20260222T025510Z.json.20260222T025536Z.audit.json`
- Audit status: `PASSED`
- Audit executed at: `2026-02-22T02:55:36Z`
- Latest backup log: `backup-core-20260302T102514Z.log`
- Log status: `PASS`
- Log modified: `2026-03-02 10:25`

## Restore Test Status

- Latest restore audit: `plan-20260222T024857Z.json.20260222T024929Z.audit.json`
- Audit status: `FAILED`
- Audit executed at: `2026-02-22T02:49:29Z`
- Latest restore log: `restore-test-20260222T024928Z.log`
- Log status: `FAIL`
- Log modified: `2026-02-22 02:49`

## Live Health

- Source: `<none>`
- Run `make vw-run CMD="make uptime-kuma-verify"` to refresh the live snapshot.

## Agent Loop

- Source: `artifacts/agent/agent-status.json`
- Overall state: `IDLE`
- Last cycle at: `2026-03-17T20:01:30.840627+00:00`
- Last cycle result: `idle`

| Queue State | Count |
| --- | --- |
| `pending` | `0` |
| `in_progress` | `0` |
| `completed` | `10` |
| `blocked-needs-approval` | `0` |
| `blocked-needs-human-decision` | `0` |
| `retry-later` | `0` |

| Recent Agent Outcomes | Count |
| --- | --- |
| `startup-timeout` | `0` |
| `timeout` | `0` |
| `stale-recovery` | `0` |
| `manual-intervention` | `3` |

### Attention Tasks

| Task | Status | Last Result | Result Class | Retry After |
| --- | --- | --- | --- | --- |
| `codex-add-project-handoff-packet` | `completed` | `manual-success` | `manual-intervention` | `None` |
| `codex-add-project-env-contract` | `completed` | `manual-success` | `manual-intervention` | `None` |
| `codex-add-project-runtime-skeleton` | `completed` | `manual-success` | `manual-intervention` | `None` |

## Key Endpoints

- `http://cortex-control:8085` - hosted wiki
- `http://cortex-control:3001` - Uptime Kuma
- `http://vault.thecortexstack.com` - Vaultwarden via edge Caddy + Cloudflare
- `http://minio.thecortexstack.com` - MinIO console via edge Caddy + Cloudflare
- `http://majelis:8086` - Caddy Manager UI

## Source Paths

- Plans: `plans/`
- Audits: `artifacts/audit/`
- Step logs: `artifacts/logs/`
- Inventory: `docs/inventory.md`
