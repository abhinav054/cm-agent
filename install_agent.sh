#!/usr/bin/env bash
set -euo pipefail

AGENTS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$AGENTS_HOME"

if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source "$AGENTS_HOME/.venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$AGENTS_HOME"

echo "Installed Mate."
echo "Run with a new temporary workspace: $AGENTS_HOME/run_agent.sh"
echo "Run from any project with: $AGENTS_HOME/run_agent.sh /path/to/workspace"
