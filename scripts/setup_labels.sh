#!/usr/bin/env bash
# Create standard GitHub labels for watchtower job queue
set -euo pipefail

REPO="${1:-sr320/public-omics-watchtower}"

create_label() {
  local name="$1" color="$2" description="${3:-}"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force
}

create_label "job:discover" "1D76DB" "Discovery job"
create_label "job:download" "0E8A16" "Download job"
create_label "job:analyze" "FBCA04" "Analysis job"
create_label "job:report" "D93F0B" "Report job"
create_label "status:queued" "C5DEF5" "Ready to claim"
create_label "status:running" "FEF2C0" "In progress"
create_label "status:completed" "0E8A16" "Successfully completed"
create_label "status:failed" "B60205" "Failed"
create_label "priority:high" "B60205" "High priority"
create_label "priority:normal" "FBCA04" "Normal priority"
create_label "priority:low" "C5DEF5" "Low priority"
create_label "species:crassostrea_gigas" "5319E7" "Pacific oyster"
create_label "needs:human" "E99695" "Requires manual review"

echo "Labels created for $REPO"
