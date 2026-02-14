# Plan Validate Execute Runbook

## Lifecycle

1. Generate a plan:
   - `make plan`
   - Optional approval demo template: `make plan TEMPLATE=approval-demo`
2. Validate the plan integrity and schema:
   - `make validate-plan PLAN=plans/<plan-file>.json`
3. Approve the plan when required:
   - `make approve PLAN=plans/<plan-file>.json VAULTWARDEN_ITEM_ID=<id>`
4. Execute the validated plan:
   - `make execute PLAN=plans/<plan-file>.json`

Validation includes command-policy checks from `policies/command-policy.json`.

## Storage Locations

- Plans and integrity files:
  - `plans/<name>.json`
  - `plans/<name>.json.sha256`
  - `plans/<name>.json.approved` (when approval is required)
- Execution audit logs:
  - `artifacts/audit/<plan>.{timestamp}.audit.json`
- Command policy:
  - `policies/command-policy.json`

## Command Policy Behavior

Each action command is evaluated deterministically in this order:

1. Deny patterns: immediate failure.
2. Env allowlist (`plan.env`): if command is not allowed in that env, fail.
3. Approval patterns or `destructive: true`: require approval file.
4. Otherwise: allow.

Validation prints one policy decision line per action:

- `[POLICY] action_id=<id> decision=ALLOW|DENY|REQUIRE_APPROVAL reason=<text>`

Policy examples:

- Denied:
  - `rm -rf /`
  - `terraform destroy`
- Requires approval:
  - `terraform apply`
  - `docker compose up`
- Allowed in `dev`:
  - `make ...`
  - `python3 ...`
  - `git ...`
  - `echo ...`
- Allowed in `prod` (initial strict mode):
  - `make validate`
  - `python3 ops/...`

## Destructive Approval Rule

If any action has `destructive: true`, execution requires:

- `plans/<plan-file>.json.approved` written by `make approve`
- Required approval keys:
  - `vaultwarden_item_id: <...>`
  - `plan_sha256: <sha256>`
  - `approved_at: <UTC timestamp>` (recommended and written by helper)

Approval is also required when any action matches a `require_approval` policy pattern, even when `destructive` is `false`.

Approvals are bound to plan content by hash. Validation recomputes canonical JSON SHA256 and fails if `plan_sha256` in `.approved` does not match the computed hash.

### Approval Workflow

1. `make validate-plan PLAN=plans/<file>.json` may fail with missing approval when policy requires it.
2. Run:
   - `make approve PLAN=plans/<file>.json VAULTWARDEN_ITEM_ID=<id>`
3. Re-run:
   - `make validate-plan PLAN=plans/<file>.json`
4. Execute:
   - `make execute PLAN=plans/<file>.json`

Only a Vaultwarden item ID reference is required. Do not place tokens, passwords, or other secrets in plans, approvals, logs, or docs.
