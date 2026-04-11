#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

# First-pass: delegates to test-system.sh which builds the environment from
# scratch (bootstrap → db_setup → startup_lifecycle → backend_suite, fail-fast).
# AI agents should run test-real-failfast.sh (or test-system.sh directly) before
# this broader gate.
./app/scripts/test-real-failfast.sh

# Supplemental: coverage report (add-on to the first-pass backend run)
if ./.venv/bin/python -c "import pytest_cov" >/dev/null 2>&1; then
  ./.venv/bin/pytest -c app/pytest.ini -q --cov=app/backend --cov-report=term-missing -m "not smoke" app/tests/
fi

node app/scripts/check-ui-page-entry-modules.mjs

if [[ "${SKIP_PLAYWRIGHT_ROUTE_COVERAGE:-0}" != "1" ]]; then
  npm --prefix app/ui run test:e2e:coverage
fi

cd "$WORKSPACE_ROOT/app/ui"
npm test
npm run build
