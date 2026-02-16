# Vaultwarden Recovery Runbook

## Symptoms

- Cloudflare returns `502` for Vaultwarden.
- `core-vaultwarden-1` is restarting/crashlooping.
- Vaultwarden logs include `no such table: twofactor`.

## Fast Triage

Check container status:

```bash
docker ps --filter name=core-vaultwarden-1 --format '{{.Names}} {{.Status}}'
```

Check service health endpoint from inside the container:

```bash
docker exec core-vaultwarden-1 sh -ec 'curl -fsS -o /dev/null -w "%{http_code}" http://127.0.0.1:80/api/config'
```

Tail recent logs:

```bash
docker logs --tail 80 core-vaultwarden-1
```

## Fix (Missing `twofactor` Table)

Stop Vaultwarden:

```bash
docker compose -f bootstrap/compose/core/docker-compose.yml stop vaultwarden
```

Identify the active volume mounted at `/data`:

```bash
docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' core-vaultwarden-1
```

Patch the active DB in that mounted volume (exact recovery commands used):

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
docker run --rm -e TS="$TS" -v core_vaultwarden_data:/data alpine sh -ec "
  apk add --no-cache sqlite >/dev/null
  test -f /data/db.sqlite3
  cp /data/db.sqlite3 /data/db.sqlite3.bak.\"$TS\"
  EXISTS=\$(sqlite3 /data/db.sqlite3 \"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='twofactor';\")
  echo twofactor_before=\$EXISTS
  if [ \"\$EXISTS\" = \"0\" ]; then
    sqlite3 /data/db.sqlite3 \"CREATE TABLE IF NOT EXISTS twofactor (uuid TEXT PRIMARY KEY NOT NULL, user_uuid TEXT NOT NULL, atype INTEGER NOT NULL, enabled BOOLEAN NOT NULL, data TEXT NOT NULL, last_used BIGINT NOT NULL);\"
  fi
  EXISTS_AFTER=\$(sqlite3 /data/db.sqlite3 \"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='twofactor';\")
  echo twofactor_after=\$EXISTS_AFTER
"
```

Restart Vaultwarden and verify:

```bash
docker compose -f bootstrap/compose/core/docker-compose.yml up -d vaultwarden
docker ps --filter name=core-vaultwarden-1 --format '{{.Names}} {{.Status}}'
docker exec core-vaultwarden-1 sh -ec 'curl -fsS -o /dev/null -w "%{http_code}" http://127.0.0.1:80/api/config'
```

Expected verification:

- Container shows `Up` (and eventually healthy).
- `/api/config` returns `200`.

## Prevention

- Set Vaultwarden sqlite `DATABASE_URL` to a file path, for example:
  - `/data/db.sqlite3`
- Avoid experimental URI formats that can point to or initialize a different DB path and cause schema mismatch/crash loops.
