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
