# Ops Status

Generated: 2026-03-08 10:16 (local)

## Summary

| Item | Value |
| --- | --- |
| Latest plan | `plan-20260222T025510Z.json` |
| Latest audit status | `PASSED` |
| Latest backup status | `PASS` |
| Latest restore-test status | `FAIL` |
| Live health | `UNKNOWN` |

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
