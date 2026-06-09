#!/usr/bin/env bash
# Install launchd worker service
set -euo pipefail

NODE_ID=""
APP_DIR="${APP_DIR:-/opt/watchtower/app}"
DATA_ROOT="${DATA_ROOT:-/Volumes/omics/watchtower}"

usage() {
  echo "Usage: $0 --node-id oyster-mini-01"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --node-id) NODE_ID="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$NODE_ID" ]] || usage

PLIST_SRC="$APP_DIR/deploy/macos/launchd/com.uw.watchtower.worker.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.uw.watchtower.worker.plist"

sed -e "s|__NODE_ID__|${NODE_ID}|g" \
    -e "s|__APP_DIR__|${APP_DIR}|g" \
    -e "s|__DATA_ROOT__|${DATA_ROOT}|g" \
    "$PLIST_SRC" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "Worker installed for node ${NODE_ID}"
echo "Logs: ${DATA_ROOT}/logs/worker.log"
