#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

frontend_has_script() {
  node -e 'const fs = require("fs"); const pkg = JSON.parse(fs.readFileSync(process.argv[1], "utf8")); const scripts = pkg.scripts || {}; process.exit(Object.prototype.hasOwnProperty.call(scripts, process.argv[2]) ? 0 : 1);' \
    "$WORKSPACE_ROOT/frontend/package.json" \
    "$1"
}

run_frontend_workspace_checks() {
  (
    cd "$WORKSPACE_ROOT/frontend"
    npm install
    npm test
    if frontend_has_script build; then
      npm run build
    else
      echo "[malcom] Hosted frontend workspace has no build script; skipping build."
    fi
  )
}

npm --prefix app/ui run test:e2e:coverage
SKIP_PLAYWRIGHT_ROUTE_COVERAGE=1 SKIP_FRONTEND_WORKSPACE_CHECKS=1 ./app/scripts/test-precommit.sh
./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_smoke_matrix.py -m smoke
run_frontend_workspace_checks

cd "$WORKSPACE_ROOT/app/ui"
npm run test:e2e
