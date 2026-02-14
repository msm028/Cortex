# Plan Validate Execute Runbook

## Lifecycle

1. Generate a plan:
   - `make plan`
2. Validate the plan integrity and schema:
   - `make validate-plan PLAN=plans/<plan-file>.json`
3. Execute the validated plan:
   - `make execute PLAN=plans/<plan-file>.json`

Validation includes command-policy checks from `policies/command-policy.json`.

## Storage Locations

- Plans and integrity files:
  - `plans/<name>.json`
  - `plans/<name>.json.sha256`
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

- `plans/<plan-file>.json.approved`
- The approval file must include:
  - `vaultwarden_item_id: <...>`

Approval is also required when any action matches a `require_approval` policy pattern, even when `destructive` is `false`.

Only a Vaultwarden item ID reference is required. Do not place tokens, passwords, or other secrets in plans, approvals, logs, or docs.
