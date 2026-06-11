#!/usr/bin/env bash
# Completely uninstall watchtower from an Apple Silicon Mac mini.
#
# Reverses everything bootstrap.sh and install_worker.sh set up:
#   - launchd worker service (LaunchAgent plist)
#   - conda/mamba `watchtower` environment
#   - Nextflow binary
#   - pip editable install of the watchtower package
#   - app directory (/opt/watchtower/app)
#   - data root (/Volumes/omics/watchtower)  [only with --purge-data]
#
# Data is preserved by default. Pass --purge-data to also delete the data root
# (raw downloads, runs, reports, logs, backups, references, SQLite DBs).
#
# Usage:
#   ./deploy/macos/uninstall.sh                 # interactive, keeps data
#   ./deploy/macos/uninstall.sh --yes           # no prompts, keeps data
#   ./deploy/macos/uninstall.sh --purge-data    # also delete the data root
#   ./deploy/macos/uninstall.sh --dry-run       # show what would happen
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/watchtower/app}"
DATA_ROOT="${DATA_ROOT:-/Volumes/omics/watchtower}"
ENV_NAME="${ENV_NAME:-watchtower}"
PLIST_LABEL="com.uw.watchtower.worker"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

ASSUME_YES=0
PURGE_DATA=0
DRY_RUN=0

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)      ASSUME_YES=1; shift ;;
    --purge-data)  PURGE_DATA=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    -h|--help)     usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY-RUN: $*"
  else
    eval "$@"
  fi
}

confirm() {
  [[ $ASSUME_YES -eq 1 ]] && return 0
  local reply
  read -r -p "$1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

echo "==> watchtower uninstall"
echo "    App dir   : $APP_DIR"
echo "    Data root : $DATA_ROOT"
echo "    Conda env : $ENV_NAME"
[[ $DRY_RUN -eq 1 ]] && echo "    (dry run — nothing will be changed)"
echo

if [[ $ASSUME_YES -eq 0 && $DRY_RUN -eq 0 ]]; then
  confirm "Proceed with uninstall?" || { echo "Aborted."; exit 0; }
fi

# 1. Stop and remove the launchd worker service.
echo "==> Removing launchd worker service"
if [[ -f "$PLIST_DEST" ]]; then
  run "launchctl unload '$PLIST_DEST' 2>/dev/null || true"
  run "rm -f '$PLIST_DEST'"
else
  echo "    No LaunchAgent at $PLIST_DEST (skipping)"
fi
# Belt and suspenders: tear down any lingering bootout reference.
run "launchctl bootout gui/$(id -u)/${PLIST_LABEL} 2>/dev/null || true"

# 2. Remove the conda/mamba environment.
echo "==> Removing conda environment '$ENV_NAME'"
CONDA_BIN=""
if command -v mamba &>/dev/null; then
  CONDA_BIN="mamba"
elif command -v conda &>/dev/null; then
  CONDA_BIN="conda"
fi
if [[ -n "$CONDA_BIN" ]]; then
  if $CONDA_BIN env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    run "$CONDA_BIN env remove -n '$ENV_NAME' --yes"
  else
    echo "    Env '$ENV_NAME' not found (skipping)"
  fi
else
  echo "    Neither mamba nor conda found (skipping env removal)"
fi

# 3. Uninstall the pip editable package (in case it lives outside the env).
echo "==> Removing pip 'watchtower' package (if present in base/python)"
if command -v pip &>/dev/null && pip show watchtower &>/dev/null; then
  run "pip uninstall -y watchtower || true"
else
  echo "    Not installed in current pip (skipping)"
fi

# 4. Remove the Nextflow binary that bootstrap installed.
echo "==> Removing Nextflow binary"
for nf in /usr/local/bin/nextflow "$HOME/.local/bin/nextflow"; do
  if [[ -f "$nf" ]]; then
    if [[ -w "$(dirname "$nf")" ]]; then
      run "rm -f '$nf'"
    else
      run "sudo rm -f '$nf'"
    fi
    echo "    Removed $nf"
  fi
done
# Nextflow's cache and assets.
[[ -d "$HOME/.nextflow" ]] && run "rm -rf '$HOME/.nextflow'"

# 5. Remove the application directory.
echo "==> Removing app directory"
if [[ -d "$APP_DIR" ]]; then
  if confirm "Delete app directory $APP_DIR?"; then
    if [[ -w "$(dirname "$APP_DIR")" ]]; then
      run "rm -rf '$APP_DIR'"
    else
      run "sudo rm -rf '$APP_DIR'"
    fi
  else
    echo "    Keeping $APP_DIR"
  fi
else
  echo "    $APP_DIR not found (skipping)"
fi

# 6. Optionally remove the data root.
echo "==> Data root"
if [[ $PURGE_DATA -eq 1 ]]; then
  if [[ -d "$DATA_ROOT" ]]; then
    if confirm "PERMANENTLY DELETE all data under $DATA_ROOT?"; then
      run "rm -rf '$DATA_ROOT'"
    else
      echo "    Keeping $DATA_ROOT"
    fi
  else
    echo "    $DATA_ROOT not found (skipping)"
  fi
else
  echo "    Preserved (run with --purge-data to delete $DATA_ROOT)"
fi

echo
echo "==> Uninstall complete."
echo "    Not touched (shared / system tools): Homebrew, mambaforge itself,"
echo "    and packages 'git'/'jq' installed via brew. Remove those manually if"
echo "    no other tools depend on them:"
echo "      brew uninstall jq          # git is usually wanted by other tools"
echo "      rm -rf \"\$HOME/mambaforge\"   # only if nothing else uses conda"
