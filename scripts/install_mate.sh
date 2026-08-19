#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/mate}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RELEASE_URL="${RELEASE_URL:-}"
SOURCE_DIR="${SOURCE_DIR:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4.1-mini}"

if [[ -z "$SOURCE_DIR" && -z "$RELEASE_URL" ]]; then
  echo "Set RELEASE_URL to a Mate release tarball URL, or SOURCE_DIR to a local Mate source folder." >&2
  echo "Example: RELEASE_URL=https://github.com/OWNER/REPO/releases/download/v0.1.0/mate-0.1.0.tar.gz bash install_mate.sh" >&2
  exit 1
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
