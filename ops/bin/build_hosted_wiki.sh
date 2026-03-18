#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ops/bin/build_hosted_wiki.sh [--overlay-ops-status artifacts/generated/ops-status.md]

Builds and starts the hosted wiki stack. When an overlay file is provided, a
temporary staged repo copy is created so live host-generated docs can be
published without mutating tracked files in the deployment checkout.
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OVERLAY_OPS_STATUS=""
STAGED_ROOT="$REPO_ROOT"
TEMP_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --overlay-ops-status)
      OVERLAY_OPS_STATUS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[FAIL] Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT

if [[ -n "$OVERLAY_OPS_STATUS" ]]; then
  if [[ ! -f "$OVERLAY_OPS_STATUS" ]]; then
    echo "[FAIL] Overlay ops-status file not found: $OVERLAY_OPS_STATUS" >&2
    exit 1
  fi
  TEMP_DIR="$(mktemp -d /tmp/cortex-wiki-build.XXXXXX)"
  STAGED_ROOT="$TEMP_DIR/repo"
  mkdir -p "$STAGED_ROOT"
  rsync -a \
    --exclude '.git/' \
    --exclude 'site/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    "$REPO_ROOT/" "$STAGED_ROOT/"
  install -D "$OVERLAY_OPS_STATUS" "$STAGED_ROOT/docs/ops-status.md"
fi

cd "$REPO_ROOT"
REPO_ROOT="$STAGED_ROOT" docker compose -f bootstrap/compose/wiki/docker-compose.yml run --rm wiki-build
REPO_ROOT="$STAGED_ROOT" docker compose -f bootstrap/compose/wiki/docker-compose.yml up -d wiki wiki-proxy
