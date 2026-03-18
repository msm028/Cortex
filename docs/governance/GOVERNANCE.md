# GOVERNANCE

## Non-negotiables
- Deterministic over probabilistic
- Plan before Execute
- Least privilege everywhere
- Git is source of truth
- Recovery > Availability

(See 02-governance-rules.md for canonical rules.)

## Plan → Validate → Execute lifecycle
1) Plan
- structured plan artifact is created
- no writes
- no secret retrieval

2) Validate (Iron Gate)
- deterministic validator is authoritative
- destructive actions require approval
- execution blocked on validate failure

3) Approve (when required)
Approval file must include:
- vaultwarden_item_id
- plan_sha256
- approved_at

4) Execute
- Dev: allowed after validator PASS (and approval if required by policy)
- Prod: validator PASS + explicit human approval and elevation rules

## Secrets handling
- No secrets in: Git, markdown, plans, logs, prompts
- Repo stores only Vaultwarden item IDs and selectors
- Runtime injection uses `BW_SESSION` + vw-run
- BW_SESSION must never be passed into child env (strip BW_* from executed processes)

## MCP / Agent Tooling Rules
- FS MCP + Ripgrep MCP may write to:
  - `docs/`
  - `infra/`
- Agents must NEVER execute `terraform apply` (manual human step only).
- Agents may generate Terraform configuration and documentation updates only.
- “Apply” remains a human CLI action.

## Documentation Rule (“Wiki-First”)
- Docs are authoritative
- Every build chunk updates docs and runbooks
- Inventory is auto-generated from tracked IaC state/artifacts plus project/runtime declarations
