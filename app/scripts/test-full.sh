#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

npm --prefix app/ui run test:e2e:coverage
SKIP_PLAYWRIGHT_ROUTE_COVERAGE=1 ./app/scripts/test-precommit.sh
./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_smoke_matrix.py -m smoke

cd "$WORKSPACE_ROOT/app/ui"
npm run test:e2e
