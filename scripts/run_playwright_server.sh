#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-4173}"

if command -v lsof >/dev/null 2>&1; then
	if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
		echo "[playwright-server] Port $PORT is already in use. Existing listeners:" >&2
		lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
		exit 1
	fi
fi

"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/reset_playwright_test_db.py"
exec "$ROOT_DIR/.venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT"
