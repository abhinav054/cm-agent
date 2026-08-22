#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-mate-release-test}"
REPO="${REPO:-abhinav054/mate}"
RELEASE_URL="${RELEASE_URL:-}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$PWD}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
MATE_KEYS_FILE="${MATE_KEYS_FILE:-$ROOT_DIR/.mate/keys.env}"
USE_DEFAULT_CMD=0
if [[ "${1:-}" == "--smoke" ]]; then
  USE_DEFAULT_CMD=1
  shift
fi

container_cmd=("$@")
if [[ "$USE_DEFAULT_CMD" != "1" && $# -eq 0 ]]; then
  container_cmd=(mate /workspace)
fi

load_env_file() {
  local env_file="$1"
  local line key value

  [[ -f "$env_file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -n "$line" && "${line:0:1}" != "#" && "$line" == *=* ]] || continue

    key="${line%%=*}"
    value="${line#*=}"
    key="${key#export }"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    if [[ -n "$key" && -z "${!key:-}" ]]; then
      printf -v "$key" '%s' "$value"
      export "$key"
    fi
  done < "$env_file"
}

load_env_file "$ENV_FILE"
load_env_file "$MATE_KEYS_FILE"

OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4.1-mini}"
if [[ -n "$OPENAI_API_KEY" ]]; then
  OPENAI_API_KEY_DISPLAY="${OPENAI_API_KEY:0:4}...${OPENAI_API_KEY: -4}"
else
  OPENAI_API_KEY_DISPLAY="<empty>"
fi

latest_release_url() {
  local release_metadata release_metadata_url release_url

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to discover the latest Mate release." >&2
    return 1
  fi

  release_metadata_url="https://github.com/$REPO/releases/latest/download/latest-release.txt"
  if ! release_metadata="$(curl -fsSL "$release_metadata_url" 2>/dev/null)"; then
    echo "Could not download latest release metadata: $release_metadata_url" >&2
    return 1
  fi

  release_url="$(printf '%s\n' "$release_metadata" | sed -n 's/^bundle_url=//p' | head -n 1)"
  if [[ -z "$release_url" ]]; then
    echo "Latest release metadata did not include bundle_url." >&2
    return 1
  fi
  if [[ "$release_url" != *-bundle.tar.gz ]]; then
    echo "Latest release metadata bundle_url is not a bundle tarball: $release_url" >&2
    return 1
  fi

  printf '%s\n' "$release_url"
}

if [[ -z "$RELEASE_URL" ]]; then
  RELEASE_URL="$(latest_release_url)"
fi
RELEASE_CACHE_KEY="$RELEASE_URL"

echo "Building Docker image from Mate tarball:"
echo "  $RELEASE_URL"

docker build \
  -f "$ROOT_DIR/docker_test/Dockerfile" \
  --build-arg "RELEASE_URL=$RELEASE_URL" \
  --build-arg "RELEASE_CACHE_KEY=$RELEASE_CACHE_KEY" \
  -t "$IMAGE_TAG" \
  "$ROOT_DIR"

run_args=(--rm --init)
if [[ -t 0 && -t 1 ]]; then
  run_args+=(-it)
fi

run_args+=(
  -e "OPENAI_API_KEY=$OPENAI_API_KEY"
  -e "OPENAI_BASE_URL=$OPENAI_BASE_URL"
  -e "OPENAI_MODEL=$OPENAI_MODEL"
  -v "$WORKSPACE_DIR:/workspace"
)

echo "Running Docker image with model provider settings:"
echo "  OPENAI_API_KEY=$OPENAI_API_KEY_DISPLAY"
echo "  OPENAI_BASE_URL=$OPENAI_BASE_URL"
echo "  OPENAI_MODEL=$OPENAI_MODEL"

if [[ "$USE_DEFAULT_CMD" == "1" ]]; then
  docker run "${run_args[@]}" "$IMAGE_TAG"
else
  docker run "${run_args[@]}" "$IMAGE_TAG" "${container_cmd[@]}"
fi
