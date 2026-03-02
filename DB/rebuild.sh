#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLM_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${LLM_DIR}"

# Usage examples:
#   ./DB/rebuild.sh
#   ./DB/rebuild.sh --no-reset
if command -v uv >/dev/null 2>&1; then
  uv run python DB/rebuild_from_data.py "$@"
elif [ -x "${LLM_DIR}/.venv/bin/python" ]; then
  "${LLM_DIR}/.venv/bin/python" DB/rebuild_from_data.py "$@"
else
  python3 DB/rebuild_from_data.py "$@"
fi
