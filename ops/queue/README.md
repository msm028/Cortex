# Agent Queue

Queue definitions for the unattended Cortex agent loop live here.

Each `*.json` file describes one unit of work. Runtime state is not stored in this folder. The loop writes task state, approvals, and status artifacts under `artifacts/agent/`.

## Task File Shape

```json
{
  "id": "project-platform-contract",
  "title": "Draft project infrastructure contract",
  "summary": "Create the first project.yaml schema and validate the docs.",
  "priority": 100,
  "approval_required": false,
  "max_attempts": 3,
  "retry_delay_seconds": 1800,
  "model_hint": "low",
  "actions": [
    {
      "argv": ["python3", "-m", "unittest", "-v", "ops.tests.test_agent_loop"],
      "cwd": ".",
      "timeout_seconds": 300
    }
  ]
}
```

## Notes

- Lower `priority` runs first.
- `approval_required: true` means the task will stop at `blocked-needs-approval` until approved through `make agent-approve TASK=<id>`.
- `model_hint` is used for Codex-backed tasks when `CODEX_LOW_MODEL`, `CODEX_HIGH_MODEL`, or `CODEX_DEFAULT_MODEL` are set in the loop environment.
- `timeout_seconds` is optional per action. For `codex_exec`, the loop defaults to `CODEX_EXEC_TIMEOUT_SECONDS` or 900 seconds when unset.
- `heartbeat_seconds` is optional per action. For `codex_exec`, the loop defaults to `CODEX_EXEC_HEARTBEAT_SECONDS` or 30 seconds when unset.
- Keep queue files deterministic and repo-safe. Do not put secrets in task files.

## Action Types

### `shell`

```json
{
  "argv": ["python3", "-m", "unittest", "-v", "ops.tests.test_agent_loop"],
  "cwd": ".",
  "timeout_seconds": 300,
  "heartbeat_seconds": 60
}
```

### `codex_exec`

```json
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
```

`codex_exec` uses the local `codex exec` CLI. Model selection is resolved from the loop environment:

- `CODEX_LOW_MODEL`
- `CODEX_HIGH_MODEL`
- `CODEX_DEFAULT_MODEL`

Timeout behavior:

- `timeout_seconds`: optional per action override
- `heartbeat_seconds`: optional per action override
- `CODEX_EXEC_TIMEOUT_SECONDS`: default timeout for `codex_exec` when no per-action timeout is set
- `CODEX_EXEC_HEARTBEAT_SECONDS`: default heartbeat interval for `codex_exec` when no per-action heartbeat is set
- `AGENT_ACTION_TIMEOUT_SECONDS`: optional default timeout for `shell` actions
- `AGENT_ACTION_HEARTBEAT_SECONDS`: optional default heartbeat interval for `shell` actions

## Examples

Example manifests live in `ops/queue/examples/`.
