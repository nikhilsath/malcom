#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="$WORKSPACE_ROOT/app"
PORT="${1:-4173}"

if command -v lsof >/dev/null 2>&1; then
	if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
		echo "[playwright-server] Port $PORT is already in use. Existing listeners:" >&2
		lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
		exit 1
	fi
fi

cd "$APP_DIR"
# Ensure Postgres runtime is accessible and the test database exists before reset.
"$WORKSPACE_ROOT/.venv/bin/python" scripts/require_test_database.py --phase full
"$WORKSPACE_ROOT/.venv/bin/python" scripts/reset_playwright_test_db.py
exec "$WORKSPACE_ROOT/.venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT"
