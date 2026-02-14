# Plan Validate Execute Runbook

## Lifecycle

1. Generate a plan:
   - `make plan`
2. Validate the plan integrity and schema:
   - `make validate-plan PLAN=plans/<plan-file>.json`
3. Execute the validated plan:
   - `make execute PLAN=plans/<plan-file>.json`

## Storage Locations

- Plans and integrity files:
  - `plans/<name>.json`
  - `plans/<name>.json.sha256`
- Execution audit logs:
  - `artifacts/audit/<plan>.{timestamp}.audit.json`

## Destructive Approval Rule

If any action has `destructive: true`, execution requires:

- `plans/<plan-file>.json.approved`
- The approval file must include:
  - `vaultwarden_item_id: <...>`

Only a Vaultwarden item ID reference is required. Do not place tokens, passwords, or other secrets in plans, approvals, logs, or docs.
