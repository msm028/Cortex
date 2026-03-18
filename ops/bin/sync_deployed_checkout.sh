#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ops/bin/sync_deployed_checkout.sh --bundle /tmp/cortex-main-<sha>.bundle [--bundle-branch main] [--refresh-wiki]
  ops/bin/sync_deployed_checkout.sh --remote origin --ref main [--refresh-wiki]

Purpose:
  Fast-forward a deployed Cortex Governor checkout while handling generated
  host-local docs such as docs/ops-status.md.
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_PATH=""
BUNDLE_BRANCH="main"
REMOTE_NAME=""
REMOTE_REF=""
REFRESH_WIKI=0
GENERATED_PATHS=("docs/ops-status.md")
STASH_NAME="auto-sync-generated-docs"
STASH_CREATED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle)
      BUNDLE_PATH="${2:-}"
      shift 2
      ;;
    --bundle-branch)
      BUNDLE_BRANCH="${2:-}"
      shift 2
      ;;
    --remote)
      REMOTE_NAME="${2:-}"
      shift 2
      ;;
    --ref)
      REMOTE_REF="${2:-}"
      shift 2
      ;;
    --refresh-wiki)
      REFRESH_WIKI=1
      shift
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

if [[ -n "$BUNDLE_PATH" && -n "$REMOTE_NAME" ]]; then
  echo "[FAIL] Use either --bundle or --remote/--ref, not both." >&2
  exit 1
fi

if [[ -z "$BUNDLE_PATH" && -z "$REMOTE_NAME" ]]; then
  echo "[FAIL] Provide --bundle or --remote/--ref." >&2
  exit 1
fi

if [[ -n "$REMOTE_NAME" && -z "$REMOTE_REF" ]]; then
  echo "[FAIL] --remote requires --ref." >&2
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "[FAIL] $REPO_ROOT is not a Git checkout." >&2
  exit 1
fi

stash_generated_paths() {
  if git diff --quiet -- "${GENERATED_PATHS[@]}" && git diff --cached --quiet -- "${GENERATED_PATHS[@]}"; then
    return 0
  fi

  local before after
  before="$(git stash list | wc -l | tr -d ' ')"
  git stash push -m "$STASH_NAME" -- "${GENERATED_PATHS[@]}" >/dev/null
  after="$(git stash list | wc -l | tr -d ' ')"
  if [[ "$after" != "$before" ]]; then
    STASH_CREATED=1
  fi
}

drop_generated_stash() {
  if [[ "$STASH_CREATED" -eq 1 ]]; then
    git stash drop --quiet stash@{0} || true
  fi
}

fetch_target_ref() {
  if [[ -n "$BUNDLE_PATH" ]]; then
    if [[ ! -f "$BUNDLE_PATH" ]]; then
      echo "[FAIL] Bundle not found: $BUNDLE_PATH" >&2
      exit 1
    fi
    local target_ref="bundle-sync-target"
    git fetch "$BUNDLE_PATH" "${BUNDLE_BRANCH}:${target_ref}" >/dev/null
    echo "$target_ref"
    return 0
  fi

  git fetch "$REMOTE_NAME" "$REMOTE_REF" >/dev/null
  echo "FETCH_HEAD"
}

rebuild_wiki() {
  ops/bin/build_hosted_wiki.sh
  curl -fsS http://127.0.0.1:8085/ >/dev/null
}

cleanup() {
  if [[ "$?" -ne 0 ]]; then
    echo "[FAIL] sync_deployed_checkout aborted." >&2
  fi
}
trap cleanup EXIT

stash_generated_paths
TARGET_REF="$(fetch_target_ref)"
git merge --ff-only "$TARGET_REF"
if [[ "$REFRESH_WIKI" -eq 1 ]]; then
  rebuild_wiki
fi
drop_generated_stash

echo "SYNC-DEPLOYED-CHECKOUT: PASS"
echo "HEAD: $(git rev-parse --short HEAD)"
