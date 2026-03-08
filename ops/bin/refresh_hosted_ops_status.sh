#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${UPTIME_KUMA_BASE_URL:-}" || -z "${UPTIME_KUMA_USERNAME:-}" || -z "${UPTIME_KUMA_PASSWORD:-}" ]]; then
  echo "[FAIL] Missing one or more required UPTIME_KUMA_* environment variables." >&2
  exit 1
fi

docker run --rm --network host \
  -e UPTIME_KUMA_BASE_URL \
  -e UPTIME_KUMA_USERNAME \
  -e UPTIME_KUMA_PASSWORD \
  -v "$REPO_ROOT:/work" -w /work node:20-alpine \
  sh -ec "npm install --silent --no-save --prefix /tmp/uptime-kuma-deps socket.io-client >/dev/null && mkdir -p artifacts/status && NODE_PATH=/tmp/uptime-kuma-deps/node_modules node ops/bin/uptime_kuma_verify.js --output artifacts/status/uptime-kuma-live.json"

python3 skills/ops-status/update-ops-status.py

docker compose -f bootstrap/compose/wiki/docker-compose.yml run --rm wiki-build
docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d wiki wiki-proxy

curl -fsS http://127.0.0.1:8085/ops-status/ >/dev/null
echo "HOSTED-OPS-STATUS-REFRESH: PASS"
