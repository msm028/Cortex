# Agent Loop

## Purpose

Run a bounded unattended work loop from `majelis` so Cortex can keep moving on queued infra-tool tasks while waiting for explicit approvals on risky work.

This loop is designed for supervised autonomy:

- repo-local work can continue unattended
- approval-gated work stops cleanly
- status is written to artifacts and surfaced in the wiki-friendly ops status page

## Scope

Good fits for the unattended loop:

- documentation updates
- scaffolding and template generation
- validation and unit tests
- plan generation
- repo-safe automation tasks

Do not use unattended mode for:

- destructive infra actions without approval
- secret rotation
- live route changes without review
- broad host bootstrap without explicit guardrails

## Queue Model

Queue definitions live in:

- `ops/queue/*.json`

Runtime state lives in:

- `artifacts/agent/task-state.json`
- `artifacts/agent/loop-state.json`
- `artifacts/agent/approvals.json`
- `artifacts/agent/agent-status.json`
- `artifacts/agent/runs/*.log`

## Core Commands

Update queue status only:

```bash
make agent-status
```

`make agent-status` now surfaces recent agent outcome classes in `artifacts/agent/agent-status.json`, including `startup-timeout`, `timeout`, `stale-recovery`, and `manual-intervention`.

Run one cycle:

```bash
make agent-loop-once
```

`make agent-loop-once` only runs deterministic queue work. It intentionally skips `codex_exec` tasks.

Run continuously with default 10 minute polling:

```bash
make agent-loop
```

The installed background service runs with `--allow-codex-exec`, so it is the process that should handle model-backed queue items.

Approve a blocked task:

```bash
make agent-approve TASK=<task-id>
```

Add an approval note:

```bash
make agent-approve TASK=<task-id> NOTE="approved after review"
```

## Task Format

Minimal task file:

```json
{
  "id": "validate-docs",
  "title": "Validate docs and tests",
  "priority": 100,
  "approval_required": false,
  "max_attempts": 3,
  "retry_delay_seconds": 1800,
  "model_hint": "low",
  "actions": [
    {
      "argv": ["python3", "-m", "unittest", "-v", "ops.tests.test_agent_loop"],
      "cwd": ".",
      "timeout_seconds": 300,
      "heartbeat_seconds": 60
    }
  ]
}
```

Model-backed task example:

```json
{
  "id": "codex-project-step",
  "title": "Codex project step",
  "priority": 200,
  "approval_required": false,
  "model_hint": "low",
  "actions": [
    {
      "type": "codex_exec",
      "cwd": ".",
      "prompt": "Update the project manifest docs and tests to reflect the latest schema.",
      "model_hint": "low",
      "sandbox": "workspace-write",
      "ephemeral": true,
      "timeout_seconds": 900,
      "heartbeat_seconds": 30
    }
  ]
}
```

## Approval Behavior

If `approval_required` is `true`, the loop will mark the task as `blocked-needs-approval` until an approval artifact is written through `make agent-approve`.

This lets the queue keep moving on other safe tasks while the approval item waits for review.

## Model Guidance

`model_hint` is queue metadata and now also feeds Codex model routing when the loop environment defines model names.

Suggested convention:

- `low`: documentation, scaffolding, tests, manifests, plan generation
- `high`: architecture changes, security-sensitive work, risky recovery, final review before merge or apply

Set one or more of these in the loop environment when you want explicit model routing:

- `CODEX_LOW_MODEL`
- `CODEX_HIGH_MODEL`
- `CODEX_DEFAULT_MODEL`

Timeout control:

- `CODEX_EXEC_TIMEOUT_SECONDS`: default timeout for `codex_exec` actions when a queue item does not specify `timeout_seconds`
- `CODEX_EXEC_HEARTBEAT_SECONDS`: default heartbeat interval for `codex_exec` actions when a queue item does not specify `heartbeat_seconds`
- `AGENT_ACTION_TIMEOUT_SECONDS`: optional default timeout for plain `shell` actions
- `AGENT_ACTION_HEARTBEAT_SECONDS`: optional default heartbeat interval for plain `shell` actions
- `timeout_seconds`: optional per-action timeout override in queue definitions
- `heartbeat_seconds`: optional per-action heartbeat override in queue definitions

When an action runs long enough to cross its heartbeat interval, the loop appends a `HEARTBEAT` line to the action log so slow-progress and total stalls are easier to distinguish. When an action times out, the loop terminates the subprocess group, logs the timeout, and moves the task to `retry-later` or `blocked-needs-human-decision` if `max_attempts` is exhausted.

If a timed-out action produced no stdout, no `last-message` file, and no heartbeat before termination, the loop records a distinct startup-hang result such as `retry-scheduled-startup-timeout` instead of the generic timeout result.

Those result classes are also published into the agent status artifact and the wiki-facing ops status page so startup hangs are visible without opening the raw run logs.

If they are unset, `codex exec` falls back to its own default configuration.

## Operating Pattern

Recommended workflow:

1. enqueue a small batch of deterministic tasks
2. start `make agent-loop` in `tmux` or a service
3. check the wiki or `make agent-status` every few hours
4. approve only the tasks that should cross a risk boundary

## systemd Service

For `majelis`, prefer the user-level service. It does not require root and is a better fit for a dev/operator workstation.

### User Service (Recommended)

Repo unit:

- `bootstrap/systemd/cortex-agent-loop.user.service`

Suggested user env file:

```bash
mkdir -p ~/.config/cortex
cat >~/.config/cortex/agent-loop.env <<'EOF'
AGENT_LOOP_SLEEP=600
AGENT_LOOP_MAX_TASKS=1
CODEX_LOW_MODEL=
CODEX_HIGH_MODEL=
CODEX_EXEC_TIMEOUT_SECONDS=900
CODEX_EXEC_HEARTBEAT_SECONDS=30
EOF
```

Install and start:

```bash
mkdir -p ~/.config/systemd/user
install -m 0644 bootstrap/systemd/cortex-agent-loop.user.service ~/.config/systemd/user/cortex-agent-loop.service
systemctl --user daemon-reload
systemctl --user enable --now cortex-agent-loop.service
```

Verify:

```bash
systemctl --user status --no-pager cortex-agent-loop.service
journalctl --user -u cortex-agent-loop.service -n 100 --no-pager
```

### System Service (Optional)

The repo includes a long-running service unit for `majelis`:

- `bootstrap/systemd/cortex-agent-loop.service`

Suggested host env file:

```bash
sudo mkdir -p /etc/cortex
sudo chmod 700 /etc/cortex
sudo sh -c 'cat >/etc/cortex/agent-loop.env'
```

Example contents:

```env
AGENT_LOOP_SLEEP=600
AGENT_LOOP_MAX_TASKS=1
```

Install and start:

```bash
cd ~/repos/cortex
sudo install -m 0644 bootstrap/systemd/cortex-agent-loop.service /etc/systemd/system/cortex-agent-loop.service
sudo systemctl daemon-reload
sudo systemctl enable --now cortex-agent-loop.service
```

Verify:

```bash
sudo systemctl status --no-pager cortex-agent-loop.service
journalctl -u cortex-agent-loop.service -n 100 --no-pager
```

## Notes

- Keep queue files free of secrets.
- Keep tasks small and restartable.
- Prefer one clear outcome per task rather than large multi-step epics inside one queue item.
