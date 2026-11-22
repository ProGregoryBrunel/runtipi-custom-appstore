#!/usr/bin/env bash
# Ephemeral real-image smoke test on a GitHub-hosted Linux runner only.
set -euo pipefail

: "${RUNNER_TEMP:?GitHub Actions RUNNER_TEMP required}"
: "${GITHUB_RUN_ID:?GitHub Actions GITHUB_RUN_ID required}"
: "${AGENT_VERSION:?Agent tag required}"
: "${WEBUI_VERSION:?WebUI tag required}"

if [[ ! "$AGENT_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ||
      ! "$WEBUI_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid version tags" >&2
  exit 1
fi

project="hermesci${GITHUB_RUN_ID}"
data="${RUNNER_TEMP}/hermes-ci-${GITHUB_RUN_ID}"
mkdir -p "$data/hermes-home" "$data/opt-data" "$data/workspace"

export APP_DATA_DIR="$data"
export TZ="Etc/UTC"
export HERMES_UID=1000 HERMES_GID=1000
export HERMES_WEBUI_AGENT_CACHE_MAX=2
export API_SERVER_KEY="hermes-compat-ci-synthetic-key-2026"
export HERMES_WEBUI_PASSWORD="synthetic-ci-password-never-for-production"

compose=(docker compose --project-name "$project" -f apps/hermes-suite/docker-compose.yml)
cleanup() {
  status=$?
  if (( status != 0 )); then
    "${compose[@]}" ps || true
    "${compose[@]}" logs --tail=25 || true
  fi
  "${compose[@]}" down -v --remove-orphans --timeout 15 || true
  # Runtipi images create UID 1000-owned 0700 files. The GitHub runner is disposable.
  # Only this exact job-owned RUNNER_TEMP subtree may be cleaned as root.
  if [[ "$data" == "${RUNNER_TEMP}/hermes-ci-${GITHUB_RUN_ID}" ]]; then
    sudo rm -rf -- "$data" || true
  fi
}
trap cleanup EXIT

# The PR self-test uses the known pinned baseline without a version change.
# A scheduled candidate must generate and test the exact proposed catalog.
if [[ "${HERMES_SMOKE_BASELINE:-0}" == "1" ]]; then
  python3 - "$AGENT_VERSION" "$WEBUI_VERSION" <<'PY'
import sys
sys.path.insert(0, "scripts")
from watch_hermes_updates import read_pins
pins = read_pins(__import__("pathlib").Path("."))
assert (pins["Agent"], pins["WebUI"]) == tuple(sys.argv[1:]), "Baseline tags differ"
PY
else
  : "${AGENT_DIGEST:?Immutable Agent image digest required}"
  : "${WEBUI_DIGEST:?Immutable WebUI image digest required}"
  python3 scripts/prepare_hermes_update.py \
    --agent "$AGENT_VERSION" --webui "$WEBUI_VERSION" \
    --agent-digest "$AGENT_DIGEST" --webui-digest "$WEBUI_DIGEST" \
    --evidence "https://github.com/ProGregoryBrunel/runtipi-custom-appstore/issues/7" \
    --apply
fi

# Check the resulting Compose without echoing synthetic environment values.
"${compose[@]}" config --quiet

# No ports are published by the catalog manifest, and no VPS mounts are used.
"${compose[@]}" up --pull always --detach --wait --wait-timeout 300

# Check both real endpoints and the gateway-runtime session retirement contract.
"${compose[@]}" exec -T hermes-webui /app/venv/bin/python3 - < scripts/hermes_pair_runtime_probe.py

echo "REAL_AGENT_WEBUI_PAIR: PASS"
