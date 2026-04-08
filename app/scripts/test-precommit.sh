#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

./.venv/bin/python app/scripts/require_test_database.py
./.venv/bin/pytest -c app/pytest.ini -q app/tests/test_startup_lifecycle.py

BACKEND_ARGS=(-m "not smoke")
if ./.venv/bin/python -c "import pytest_cov" >/dev/null 2>&1; then
  BACKEND_ARGS+=(--cov=app/backend --cov-report=term-missing)
fi

./.venv/bin/pytest -c app/pytest.ini "${BACKEND_ARGS[@]}" app/tests/
node app/scripts/check-ui-page-entry-modules.mjs

if [[ "${SKIP_PLAYWRIGHT_ROUTE_COVERAGE:-0}" != "1" ]]; then
  npm --prefix app/ui run test:e2e:coverage
fi

cd "$WORKSPACE_ROOT/app/ui"
npm test
npm run build
