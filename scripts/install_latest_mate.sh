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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to install Mate." >&2
  exit 1
fi

INSTALLER="$SCRIPT_DIR/install_mate.sh"
if [[ ! -f "$INSTALLER" ]]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  INSTALLER="$TMP_DIR/install_mate.sh"
  curl -fsSL "https://raw.githubusercontent.com/$REPO/main/scripts/install_mate.sh" -o "$INSTALLER"
  chmod +x "$INSTALLER"
fi

exec "$INSTALLER" "${INSTALL_ARGS[@]}"
