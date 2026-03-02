# flywheel-runner

Runs a deterministic docs flywheel:

1. `make validate` (unless `--no-validate`)
2. optional command execution against a selected plan
3. Skill 1 docs update (`update-docs.py`)

If the selected plan contains infra/destructive indicators from `.codex/config.toml`,
execution requires both:

- `--yes`
- `--confirm-risk`

## Usage

Dry run path (validate + docs update):

```bash
python3 skills/flywheel-runner/run-flywheel.py --message "Skill 2 dry run"
```

Execute with explicit confirmation:

```bash
python3 skills/flywheel-runner/run-flywheel.py \
  --message "Skill 2 exec test" \
  --exec "echo APPLY {plan}" \
  --yes \
  --confirm-risk
```

Use specific plan:

```bash
python3 skills/flywheel-runner/run-flywheel.py \
  --message "Use explicit plan" \
  --plan plans/example.json
```

Make wrapper:

```bash
make skill-flywheel MSG="Skill 2 dry run"
make skill-flywheel MSG="Skill 2 exec test" EXEC="echo APPLY {plan}" YES=1 CONFIRM=1
```
