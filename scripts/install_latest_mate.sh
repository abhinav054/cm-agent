#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="abhinav054/mate"
INSTALL_ARGS=()

usage() {
  echo "Usage: $0 [install_mate options]"
  echo
  echo "Install options are passed through, for example:"
  echo "  --api-key KEY --base-url URL --model MODEL --install-dir DIR --bin-dir DIR"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      INSTALL_ARGS+=("$1")
      if [[ "${2:-}" != "" && "$2" != --* ]]; then
        INSTALL_ARGS+=("$2")
        shift 2
      else
        shift
      fi
      ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to download the latest Mate release." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to install Mate." >&2
  exit 1
fi

LATEST_JSON="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")"
RELEASE_URL="$(printf '%s' "$LATEST_JSON" | python3 -c '
import json
import sys

release = json.load(sys.stdin)
assets = release.get("assets", [])
for asset in assets:
    name = asset.get("name", "")
    if name.startswith("mate-") and name.endswith("-bundle.tar.gz"):
        print(asset["browser_download_url"])
        break
else:
    for asset in assets:
        name = asset.get("name", "")
        if name.startswith("mate-") and name.endswith(".tar.gz"):
            print(asset["browser_download_url"])
            break
')"

if [[ -z "$RELEASE_URL" ]]; then
  echo "Could not find a Mate release tarball on the latest release for $REPO." >&2
  exit 1
fi

echo "Installing latest Mate release from:"
echo "  $RELEASE_URL"

INSTALLER="$SCRIPT_DIR/install_mate.sh"
if [[ ! -f "$INSTALLER" ]]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  INSTALLER="$TMP_DIR/install_mate.sh"
  curl -fsSL "https://raw.githubusercontent.com/$REPO/main/scripts/install_mate.sh" -o "$INSTALLER"
  chmod +x "$INSTALLER"
fi

exec "$INSTALLER" --release-url "$RELEASE_URL" "${INSTALL_ARGS[@]}"
