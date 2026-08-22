#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

OPENAI_API_KEY='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'
OPENAI_BASE_URL='https://api.groq.com/openai/v1'
OPENAI_MODEL='openai/gpt-oss-120b'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-mate-release-test}"
REPO="${REPO:-abhinav054/mate}"
RELEASE_URL="${RELEASE_URL:-}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$PWD}"
USE_DEFAULT_CMD=0
if [[ "${1:-}" == "--smoke" ]]; then
  USE_DEFAULT_CMD=1
  shift
fi

container_cmd=("$@")
if [[ "$USE_DEFAULT_CMD" != "1" && $# -eq 0 ]]; then
  container_cmd=(mate /workspace)
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
  -e "OPENAI_API_KEY=test-key"
  -e "OPENAI_BASE_URL=https://api.openai.com/v1"
  -e "OPENAI_MODEL=gpt-4.1-mini"
  -v "$WORKSPACE_DIR:/workspace"
)

if [[ "$USE_DEFAULT_CMD" == "1" ]]; then
  docker run "${run_args[@]}" "$IMAGE_TAG"
else
  docker run "${run_args[@]}" "$IMAGE_TAG" "${container_cmd[@]}"
fi
