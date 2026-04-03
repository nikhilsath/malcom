#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

npm --prefix ui run test:e2e:coverage
SKIP_PLAYWRIGHT_ROUTE_COVERAGE=1 ./scripts/test-precommit.sh
./.venv/bin/pytest tests/test_api_smoke_matrix.py -m smoke
./.venv/bin/python scripts/test-external-probes.py

cd "$ROOT_DIR/ui"
npm run test:e2e
