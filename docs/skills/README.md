# Skills

Skills are **script-first** utilities under `/skills/*`.
They must be runnable without MCP; MCP (later) is only a transport layer.

## Skill 1: update-docs
Updates:
- `docs/CHANGELOG.md` (adds a bullet under `## Unreleased`)
- `docs/inventory.md` (updates `Last updated:`)

Run:
- `make skill-update-docs MSG="Describe the change"`
- or `python3 skills/update-docs/update-docs.py --message "Describe the change"`

Validate:
- `make validate`

## Skill 2: flywheel-runner
Runs:
- deterministic validation (`make validate`, unless skipped)
- optional command execution against a selected plan
- Skill 1 docs update with plan context in the changelog message

Run:
- `make skill-flywheel MSG="Skill 2 dry run"`
- `make skill-flywheel MSG="Skill 2 exec test" EXEC="echo APPLY {plan}" YES=1`

## Skill 3: plan-inspect
Inspects plan JSON files and prints a concise risk-oriented summary:
- plan metadata (path, mtime, size, top-level keys)
- common count heuristics (`steps/actions/operations/...`)
- infra indicator matches from `.codex/config.toml` `infra_step_examples`
- best-effort target extraction (`host/hostname/ip/address/node/target`)

Run:
- `make skill-plan-inspect`
- `make skill-plan-inspect LIST=1 N=20`
- `make skill-plan-inspect PLAN="plans/plan-xxxx.json"`
