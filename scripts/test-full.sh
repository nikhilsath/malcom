#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/test-precommit.sh
./.venv/bin/pytest tests/test_api_smoke_matrix.py -m smoke
./.venv/bin/python scripts/test-external-probes.py

cd "$ROOT_DIR/ui"
npm run test:e2e
