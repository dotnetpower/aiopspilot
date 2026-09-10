#!/usr/bin/env bash
# Reconcile legacy Job addresses that block specialized targeted plans.
set -euo pipefail

scope="${1:-rca}"
if [[ "$scope" != "rca" && "$scope" != "observability" ]]; then
  echo "usage: reconcile_rca_bootstrap_state.sh [rca|observability]" >&2
  exit 2
fi

before_digest="$(terraform state pull | sha256sum | cut -d' ' -f1)"
state_list="$(terraform state list)"

state_has() {
  grep -Fxq -- "$1" <<< "$state_list"
}

moves_from=()
moves_to=()

reconcile_address() {
  local label="$1"
  local new="$2"
  shift 2
  local legacy=()
  local candidate
  for candidate in "$@"; do
    state_has "$candidate" && legacy+=("$candidate")
  done
  if (( ${#legacy[@]} > 1 )) || { (( ${#legacy[@]} == 1 )) && state_has "$new"; }; then
    echo "legacy and current ${label} state addresses conflict" >&2
    exit 1
  fi
  if (( ${#legacy[@]} == 1 )); then
    moves_from+=("${legacy[0]}")
    moves_to+=("$new")
  fi
}

if [[ "$scope" == "rca" ]]; then
  for resource in baseline_regression pattern_growth; do
    reconcile_address \
      measurement \
      "module.measurement_runners[0].azurerm_container_app_job.${resource}[0]" \
      "module.measurement_runners[0].azurerm_container_app_job.${resource}" \
      "module.measurement_runners.azurerm_container_app_job.${resource}" \
      "module.measurement_runners.azurerm_container_app_job.${resource}[0]"
  done
else
  for resource in oob rule_watcher; do
    reconcile_address \
      observability \
      "module.compute.azurerm_container_app_job.${resource}[0]" \
      "module.compute.azurerm_container_app_job.${resource}"
  done
fi

for index in "${!moves_from[@]}"; do
  terraform state mv "${moves_from[$index]}" "${moves_to[$index]}"
done

after_digest="$(terraform state pull | sha256sum | cut -d' ' -f1)"
{
  echo "${scope^} targeted-plan state reconciliation completed."
  echo "Before digest: \`sha256:${before_digest}\`"
  echo "After digest: \`sha256:${after_digest}\`"
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
