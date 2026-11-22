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
    "${compose[@]}" logs --tail=80 || true
  fi
  "${compose[@]}" down -v --remove-orphans --timeout 15 || true
  rm -rf -- "$data"
}
trap cleanup EXIT

# Render the proposed catalog, not the currently installed compose.
python3 scripts/prepare_hermes_update.py \
  --agent "$AGENT_VERSION" --webui "$WEBUI_VERSION" \
  --evidence "https://github.com/ProGregoryBrunel/runtipi-custom-appstore/issues/7" \
  --apply

# Check the resulting Compose without echoing synthetic environment values.
"${compose[@]}" config --quiet

# No ports are published by the catalog manifest, and no VPS mounts are used.
"${compose[@]}" up --pull always --detach --wait --wait-timeout 300

# Check both real endpoints and the gateway-runtime session retirement contract.
"${compose[@]}" exec -T hermes-webui python3 - < scripts/hermes_pair_runtime_probe.py

echo "REAL_AGENT_WEBUI_PAIR: PASS"
