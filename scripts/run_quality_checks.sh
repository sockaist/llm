#!/usr/bin/env bash
set -euo pipefail

main() {
  # Optional: lint
  if command -v ruff >/dev/null 2>&1; then
    echo "[lint] ruff check"
    ruff check src || exit 1
  else
    echo "[lint] ruff not installed; skipping"
  fi

  # Optional: type check
  if command -v mypy >/dev/null 2>&1; then
    echo "[type] mypy"
    mypy src || exit 1
  else
    echo "[type] mypy not installed; skipping"
  fi

  # Smoke tests
  if command -v pytest >/dev/null 2>&1; then
    echo "[test] pytest smoke"
    pytest tests/smoke -q --maxfail=1
  else
    echo "[test] pytest not installed; skipping"
  fi
}

main "$@"
