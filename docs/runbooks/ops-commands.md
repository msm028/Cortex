# Operations Commands Runbook

## Purpose

Provide deterministic `make` wrappers for common stack operations.

## Common Commands

Bring up core and edge stacks:

```bash
make up
```

Stop edge then core stacks:

```bash
make down
```

Restart only core stack:

```bash
make restart-core
```

Tail edge service logs:

```bash
make logs-edge SERVICE=caddy
```

Optional log line count:

```bash
make logs-edge SERVICE=caddy TAIL=500
```

`logs-core` and `logs-edge` require `SERVICE`.

## Agent Loop Commands

Update unattended queue status:

```bash
make agent-status
```

This refreshes `artifacts/agent/agent-status.json`, including recent startup-timeout and timeout classifications for model-backed tasks.

Run one unattended cycle:

```bash
make agent-loop-once
```

Run the loop continuously:

```bash
make agent-loop SLEEP=600 MAX_TASKS=1
```

Approve a blocked task:

```bash
make agent-approve TASK=<task-id> NOTE="approved after review"
```

## Blast Radius Warning

`make down`, `make down-core`, and `make down-edge` stop running services. Use these commands deliberately in shared environments.
