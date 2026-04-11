#!/usr/bin/env bash
# test-system.sh — primary environment-building real-system test command.
#
# This script builds the test environment from scratch, runs all real tests,
# and writes a stable machine-readable artifact for every failure path.
#
# Usage:
#   bash app/scripts/test-system.sh
#   INCLUDE_BROWSER_SUITE=1 bash app/scripts/test-system.sh
#
# Artifact: app/tests/test-artifacts/system-result.json
#   Fields:  step          — failure stage name (see below) or "all" on success
#            exit_code     — non-zero on failure, 0 on success
#            command       — the command that failed (or "test-system.sh" on success)
#            first_error_lines — last ≤40 output lines from the failing command
#
# Step names written to the artifact:
#   bootstrap          Ensure the PostgreSQL runtime is reachable
#   db_setup           Ensure the test database exists and is migrated/initialized
#   startup_lifecycle  Run test_startup_lifecycle.py (highest-value real tests)
#   backend_suite      Run the full non-smoke pytest suite (-x)
#   browser_suite      Run Playwright e2e suite (only when INCLUDE_BROWSER_SUITE=1)
#   all                Success (exit_code: 0)
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

ARTIFACT_DIR="app/tests/test-artifacts"
ARTIFACT_FILE="$ARTIFACT_DIR/system-result.json"
mkdir -p "$ARTIFACT_DIR"

# ---------------------------------------------------------------------------
# Helper: write JSON artifact.  All values are passed via environment variables
# to avoid shell-quoting and injection issues when command strings contain
# special characters.
#
#   _TS_STEP=<step>  _TS_EXIT=<code>  _TS_CMD=<command>  _TS_OUT=<output>
# ---------------------------------------------------------------------------
write_artifact() {
  # Capture all inputs through environment variables so Python sees clean strings.
  _TS_STEP="$1" _TS_EXIT="$2" _TS_CMD="$3" _TS_OUT="$4" _TS_ARTIFACT="$ARTIFACT_FILE" \
  python3 - <<'PYEOF'
import json, os, sys

step     = os.environ["_TS_STEP"]
exit_val = int(os.environ["_TS_EXIT"])
command  = os.environ["_TS_CMD"]
output   = os.environ["_TS_OUT"]
artifact = os.environ["_TS_ARTIFACT"]

lines = output.splitlines()[-40:] if output else []

data = {
    "step":             step,
    "exit_code":        exit_val,
    "command":          command,
    "first_error_lines": lines,
}

with open(artifact, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

write_artifact_and_exit() {
  write_artifact "$1" "$2" "$3" "$4"
  exit "$2"
}

# ---------------------------------------------------------------------------
# Step 1: bootstrap — ensure PostgreSQL runtime is reachable
# ---------------------------------------------------------------------------
BOOTSTRAP_CMD=".venv/bin/python app/scripts/require_test_database.py --phase runtime"
BOOTSTRAP_OUTPUT=$(eval "$BOOTSTRAP_CMD" 2>&1) || BOOTSTRAP_EXIT=$?
BOOTSTRAP_EXIT=${BOOTSTRAP_EXIT:-0}

if [[ "$BOOTSTRAP_EXIT" -ne 0 ]]; then
  echo "bootstrap step failed"
  write_artifact_and_exit "bootstrap" "$BOOTSTRAP_EXIT" "$BOOTSTRAP_CMD" "$BOOTSTRAP_OUTPUT"
fi
echo "$BOOTSTRAP_OUTPUT"

# ---------------------------------------------------------------------------
# Step 2: db_setup — ensure test database exists and schema is initialized
# ---------------------------------------------------------------------------
DB_SETUP_CMD=".venv/bin/python app/scripts/require_test_database.py --phase db_setup"
DB_SETUP_OUTPUT=$(eval "$DB_SETUP_CMD" 2>&1) || DB_SETUP_EXIT=$?
DB_SETUP_EXIT=${DB_SETUP_EXIT:-0}

if [[ "$DB_SETUP_EXIT" -ne 0 ]]; then
  echo "db_setup step failed"
  write_artifact_and_exit "db_setup" "$DB_SETUP_EXIT" "$DB_SETUP_CMD" "$DB_SETUP_OUTPUT"
fi
echo "$DB_SETUP_OUTPUT"

# ---------------------------------------------------------------------------
# Step 3: startup_lifecycle — highest-value real tests first
# ---------------------------------------------------------------------------
LIFECYCLE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short app/tests/test_startup_lifecycle.py"
LIFECYCLE_OUTPUT=$(eval "$LIFECYCLE_CMD" 2>&1) || LIFECYCLE_EXIT=$?
LIFECYCLE_EXIT=${LIFECYCLE_EXIT:-0}

if [[ "$LIFECYCLE_EXIT" -ne 0 ]]; then
  echo "startup_lifecycle step failed"
  write_artifact_and_exit "startup_lifecycle" "$LIFECYCLE_EXIT" "$LIFECYCLE_CMD" "$LIFECYCLE_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Step 4: backend_suite — full non-smoke pytest suite (fail-fast)
# ---------------------------------------------------------------------------
SUITE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short -m \"not smoke\" app/tests/"
SUITE_OUTPUT=$(eval "$SUITE_CMD" 2>&1) || SUITE_EXIT=$?
SUITE_EXIT=${SUITE_EXIT:-0}

if [[ "$SUITE_EXIT" -ne 0 ]]; then
  echo "backend_suite step failed"
  write_artifact_and_exit "backend_suite" "$SUITE_EXIT" "$SUITE_CMD" "$SUITE_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Step 5 (optional): browser_suite — real Playwright e2e suite
# ---------------------------------------------------------------------------
if [[ "${INCLUDE_BROWSER_SUITE:-0}" == "1" ]]; then
  BROWSER_CMD="npm --prefix app/ui run test:e2e"
  BROWSER_OUTPUT=$(eval "$BROWSER_CMD" 2>&1) || BROWSER_EXIT=$?
  BROWSER_EXIT=${BROWSER_EXIT:-0}

  if [[ "$BROWSER_EXIT" -ne 0 ]]; then
    echo "browser_suite step failed"
    write_artifact_and_exit "browser_suite" "$BROWSER_EXIT" "$BROWSER_CMD" "$BROWSER_OUTPUT"
  fi
fi

# ---------------------------------------------------------------------------
# All steps passed
# ---------------------------------------------------------------------------
write_artifact "all" "0" "test-system.sh" ""
echo "All real tests passed."
