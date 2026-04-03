#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

./.venv/bin/python scripts/require_test_database.py
./.venv/bin/pytest -q tests/test_startup_lifecycle.py

BACKEND_ARGS=(-m "not smoke")
if ./.venv/bin/python -c "import pytest_cov" >/dev/null 2>&1; then
  BACKEND_ARGS+=(--cov=backend --cov-report=term-missing)
fi

./.venv/bin/pytest "${BACKEND_ARGS[@]}"
node scripts/check-ui-page-entry-modules.mjs

cd "$ROOT_DIR/ui"
npm test
npm run build
