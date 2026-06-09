#!/usr/bin/env bash
# Bootstrap watchtower on Apple Silicon Mac mini
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/watchtower/app}"
DATA_ROOT="${DATA_ROOT:-/Volumes/omics/watchtower}"

echo "==> Installing Homebrew dependencies"
if ! command -v brew &>/dev/null; then
  echo "Install Homebrew first: https://brew.sh"
  exit 1
fi
brew install git jq

echo "==> Installing mambaforge (if missing)"
if ! command -v mamba &>/dev/null; then
  curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh -o /tmp/miniforge.sh
  bash /tmp/miniforge.sh -b -p "$HOME/mambaforge"
  eval "$("$HOME/mambaforge/bin/conda" shell.bash hook)"
fi

echo "==> Creating conda environment"
cd "$APP_DIR"
mamba env create -f environment.yml --yes || mamba env update -f environment.yml --yes
eval "$(mamba shell.bash hook)"
mamba activate watchtower

echo "==> Installing Nextflow"
if ! command -v nextflow &>/dev/null; then
  curl -fsSL https://get.nextflow.io | bash
  sudo mv nextflow /usr/local/bin/ 2>/dev/null || mv nextflow "$HOME/.local/bin/"
fi

echo "==> Creating data directories"
mkdir -p "$DATA_ROOT"/{raw,runs,reports,logs,backups,references}

echo "==> Validating configuration"
watchtower config validate

echo "Bootstrap complete. Next: ./deploy/macos/install_worker.sh --node-id oyster-mini-01"
