#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/mate}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REPO="${REPO:-abhinav054/mate}"
RELEASE_URL="${RELEASE_URL:-}"
SOURCE_DIR="${SOURCE_DIR:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-}"
OPENAI_MODEL="${OPENAI_MODEL:-}"

usage() {
  echo "Usage: $0 [--release-url URL | --source-dir DIR] [--install-dir DIR] [--bin-dir DIR] [--api-key KEY] [--base-url URL] [--model MODEL]"
  echo "If neither --release-url nor --source-dir is set, the latest GitHub release tarball is used."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-url)
      RELEASE_URL="${2:-}"
      shift 2
      ;;
    --source-dir)
      SOURCE_DIR="${2:-}"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --bin-dir)
      BIN_DIR="${2:-}"
      shift 2
      ;;
    --api-key)
      OPENAI_API_KEY="${2:-}"
      shift 2
      ;;
    --base-url)
      OPENAI_BASE_URL="${2:-}"
      shift 2
      ;;
    --model)
      OPENAI_MODEL="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

latest_release_url() {
  local latest_json release_metadata_url release_url

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to discover the latest Mate release." >&2
    return 1
  fi
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "$PYTHON_BIN is required to discover the latest Mate release." >&2
    return 1
  fi

  release_metadata_url="https://github.com/$REPO/releases/latest/download/latest-release.json"
  if latest_json="$(curl -fsSL "$release_metadata_url" 2>/dev/null)"; then
    release_url="$(printf '%s' "$latest_json" | "$PYTHON_BIN" -c '
import json
import sys

release = json.load(sys.stdin)
print(release.get("bundle_url", ""))
' 2>/dev/null || true)"
    if [[ -n "$release_url" ]]; then
      printf '%s\n' "$release_url"
      return
    fi
  fi

  latest_json="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")"
  printf '%s' "$latest_json" | "$PYTHON_BIN" -c '
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
'
}

if [[ -z "$SOURCE_DIR" && -z "$RELEASE_URL" ]]; then
  RELEASE_URL="$(latest_release_url)"
  if [[ -z "$RELEASE_URL" ]]; then
    echo "Could not find a Mate release tarball on the latest release for $REPO." >&2
    exit 1
  fi
  echo "Installing latest Mate release from:"
  echo "  $RELEASE_URL"
fi

prompt_if_missing() {
  local var_name="$1"
  local prompt="$2"
  local default_value="${3:-}"
  local secret="${4:-0}"
  local current_value="${!var_name:-}"

  if [[ -n "$current_value" ]]; then
    return
  fi

  if [[ "$secret" == "1" ]]; then
    read -rsp "$prompt: " current_value
    echo
  elif [[ -n "$default_value" ]]; then
    read -rp "$prompt [$default_value]: " current_value
    current_value="${current_value:-$default_value}"
  else
    read -rp "$prompt: " current_value
  fi

  printf -v "$var_name" '%s' "$current_value"
}

prompt_if_missing OPENAI_API_KEY "OpenAI-compatible API key" "" 1
prompt_if_missing OPENAI_BASE_URL "OpenAI-compatible base URL" "https://api.openai.com/v1"
prompt_if_missing OPENAI_MODEL "OpenAI-compatible model" "gpt-4.1-mini"

quote_env_value() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [[ -n "$SOURCE_DIR" ]]; then
  cp -R "$SOURCE_DIR"/. "$TMP_DIR/source"
else
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$RELEASE_URL" -o "$TMP_DIR/mate.tar.gz"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP_DIR/mate.tar.gz" "$RELEASE_URL"
  else
    echo "Install curl or wget, then rerun this installer." >&2
    exit 1
  fi
  mkdir -p "$TMP_DIR/source"
  tar -xzf "$TMP_DIR/mate.tar.gz" -C "$TMP_DIR/source" --strip-components=1
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -R "$TMP_DIR/source"/. "$INSTALL_DIR"

if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
fi

# shellcheck disable=SC1091
source "$INSTALL_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "$INSTALL_DIR"

chmod +x "$INSTALL_DIR/run_agent.sh"
cat > "$BIN_DIR/mate" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/run_agent.sh" "\$@"
EOF
chmod +x "$BIN_DIR/mate"

if [[ ! -d "$INSTALL_DIR/.mate" ]]; then
  mkdir -p "$INSTALL_DIR/.mate"
fi

cat > "$INSTALL_DIR/.mate/keys.env" <<EOF
OPENAI_API_KEY=$(quote_env_value "$OPENAI_API_KEY")
OPENAI_BASE_URL=$(quote_env_value "$OPENAI_BASE_URL")
OPENAI_MODEL=$(quote_env_value "$OPENAI_MODEL")
EOF
chmod 600 "$INSTALL_DIR/.mate/keys.env"

echo "Mate installed."
echo "Run: $BIN_DIR/mate"
echo "Config: $INSTALL_DIR/.mate"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "Add $BIN_DIR to PATH if the mate command is not found." ;;
esac
