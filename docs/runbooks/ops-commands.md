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

## Blast Radius Warning

`make down`, `make down-core`, and `make down-edge` stop running services. Use these commands deliberately in shared environments.
