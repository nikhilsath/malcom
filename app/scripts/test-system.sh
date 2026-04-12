#!/usr/bin/env bash
# test-system.sh — canonical real-system test command.
#
# This script builds the test environment from scratch, runs all real tests
# including a minimal critical browser check, and writes a stable machine-readable
# artifact for every failure path.  It is the single command that proves the
# product can boot from zero and its critical functionality actually works.
#
# Usage:
#   bash app/scripts/test-system.sh
#   SKIP_BROWSER_SUITE=1 bash app/scripts/test-system.sh  # skip browser (local, no Playwright installed)
#   INCLUDE_FULL_BROWSER_SUITE=1 bash app/scripts/test-system.sh  # also run the full Playwright suite
#
# Artifact: app/tests/test-artifacts/system-result.json
#   Fields:  step          — failure stage name (see below) or "all" on success
#            exit_code     — non-zero on failure, 0 on success
#            command       — the command that failed (or "test-system.sh" on success)
#            first_error_lines — last ≤40 output lines from the failing command
#
# Step names written to the artifact:
#   bootstrap          Ensure the PostgreSQL runtime is reachable
#   db_setup           Reset/create the test database to a clean state each run
#   startup_lifecycle  Run test_startup_lifecycle.py (highest-value real tests)
#   backend_suite      Run the full non-smoke pytest suite (-x)
#   critical_browser   Run the minimal real Playwright subset (default ON, skip with SKIP_BROWSER_SUITE=1)
#   browser_suite      Run the full Playwright e2e suite (only when INCLUDE_FULL_BROWSER_SUITE=1)
#   all                Success (exit_code: 0)
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

ARTIFACT_DIR="${MALCOM_TEST_ARTIFACT_DIR:-app/tests/test-artifacts}"
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

run_captured_command() {
  local __result_var="$1"
  local command="$2"
  local output=""
  local exit_code=0

  output=$(eval "$command" 2>&1) || exit_code=$?
  printf -v "$__result_var" '%s' "$output"
  return "$exit_code"
}

fail_bootstrap_prerequisite() {
  local command="$1"
  local message="$2"

  echo "bootstrap prerequisite failed"
  write_artifact_and_exit "bootstrap" "1" "$command" "$message"
}

require_executable() {
  local path="$1"
  local install_hint="$2"

  if [[ ! -x "$path" ]]; then
    fail_bootstrap_prerequisite \
      "test -x $path" \
      "$path is missing or not executable. $install_hint"
  fi
}

require_directory() {
  local path="$1"
  local install_hint="$2"

  if [[ ! -d "$path" ]]; then
    fail_bootstrap_prerequisite \
      "test -d $path" \
      "$path is missing. $install_hint"
  fi
}

require_browser_prerequisites() {
  local output=""
  local check_command="cd app/ui && node -e \"const fs = require('fs'); const { chromium } = require('playwright'); const browserPath = chromium.executablePath(); if (!browserPath || !fs.existsSync(browserPath)) { console.error('Chromium browser binaries are missing. Run npm --prefix app/ui exec -- playwright install --with-deps chromium.'); process.exit(1); } console.log(browserPath);\""

  if ! command -v npm >/dev/null 2>&1; then
    fail_bootstrap_prerequisite \
      "command -v npm" \
      "npm is not installed. Install Node.js 20+ and run npm --prefix app/ui ci."
  fi

  require_directory "app/ui/node_modules" "Run npm --prefix app/ui ci."
  require_executable "app/ui/node_modules/.bin/playwright" "Run npm --prefix app/ui ci."

  if ! run_captured_command output "$check_command"; then
    fail_bootstrap_prerequisite "$check_command" "$output"
  fi
}

require_executable ".venv/bin/python" "Create the virtualenv and install backend dependencies with python3 -m venv .venv && .venv/bin/pip install -r app/requirements.txt."
require_executable ".venv/bin/pytest" "Install backend test dependencies with .venv/bin/pip install -r app/requirements.txt."

if [[ "${SKIP_BROWSER_SUITE:-0}" != "1" || "${INCLUDE_FULL_BROWSER_SUITE:-0}" == "1" ]]; then
  require_browser_prerequisites
fi

# ---------------------------------------------------------------------------
# Step 1: bootstrap — ensure PostgreSQL runtime is reachable
# ---------------------------------------------------------------------------
BOOTSTRAP_CMD=".venv/bin/python app/scripts/require_test_database.py --phase runtime"
BOOTSTRAP_OUTPUT=""
BOOTSTRAP_EXIT=0
run_captured_command BOOTSTRAP_OUTPUT "$BOOTSTRAP_CMD" || BOOTSTRAP_EXIT=$?

if [[ "$BOOTSTRAP_EXIT" -ne 0 ]]; then
  echo "bootstrap step failed"
  write_artifact_and_exit "bootstrap" "$BOOTSTRAP_EXIT" "$BOOTSTRAP_CMD" "$BOOTSTRAP_OUTPUT"
fi
echo "$BOOTSTRAP_OUTPUT"

# ---------------------------------------------------------------------------
# Step 2: db_setup — ensure test database exists and schema is initialized
# ---------------------------------------------------------------------------
DB_SETUP_CMD=".venv/bin/python app/scripts/require_test_database.py --phase db_setup"
DB_SETUP_OUTPUT=""
DB_SETUP_EXIT=0
run_captured_command DB_SETUP_OUTPUT "$DB_SETUP_CMD" || DB_SETUP_EXIT=$?

if [[ "$DB_SETUP_EXIT" -ne 0 ]]; then
  echo "db_setup step failed"
  write_artifact_and_exit "db_setup" "$DB_SETUP_EXIT" "$DB_SETUP_CMD" "$DB_SETUP_OUTPUT"
fi
echo "$DB_SETUP_OUTPUT"

# ---------------------------------------------------------------------------
# Step 3: startup_lifecycle — highest-value real tests first
# ---------------------------------------------------------------------------
LIFECYCLE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short app/tests/test_startup_lifecycle.py"
LIFECYCLE_OUTPUT=""
LIFECYCLE_EXIT=0
run_captured_command LIFECYCLE_OUTPUT "$LIFECYCLE_CMD" || LIFECYCLE_EXIT=$?

if [[ "$LIFECYCLE_EXIT" -ne 0 ]]; then
  echo "startup_lifecycle step failed"
  write_artifact_and_exit "startup_lifecycle" "$LIFECYCLE_EXIT" "$LIFECYCLE_CMD" "$LIFECYCLE_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Step 4: backend_suite — full non-smoke pytest suite (fail-fast)
# ---------------------------------------------------------------------------
SUITE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short -m \"not smoke\" app/tests/"
SUITE_OUTPUT=""
SUITE_EXIT=0
run_captured_command SUITE_OUTPUT "$SUITE_CMD" || SUITE_EXIT=$?

if [[ "$SUITE_EXIT" -ne 0 ]]; then
  echo "backend_suite step failed"
  write_artifact_and_exit "backend_suite" "$SUITE_EXIT" "$SUITE_CMD" "$SUITE_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Step 5 (default): critical_browser — minimal real Playwright subset
# Skippable with SKIP_BROWSER_SUITE=1 (e.g. local dev without browsers installed)
# ---------------------------------------------------------------------------
if [[ "${SKIP_BROWSER_SUITE:-0}" != "1" ]]; then
  CRITICAL_CMD="npm --prefix app/ui run test:e2e:critical"
  CRITICAL_OUTPUT=""
  CRITICAL_EXIT=0
  run_captured_command CRITICAL_OUTPUT "$CRITICAL_CMD" || CRITICAL_EXIT=$?

  if [[ "$CRITICAL_EXIT" -ne 0 ]]; then
    echo "critical_browser step failed"
    write_artifact_and_exit "critical_browser" "$CRITICAL_EXIT" "$CRITICAL_CMD" "$CRITICAL_OUTPUT"
  fi
fi

# ---------------------------------------------------------------------------
# Step 6 (optional): browser_suite — full Playwright e2e suite
# ---------------------------------------------------------------------------
if [[ "${INCLUDE_FULL_BROWSER_SUITE:-0}" == "1" ]]; then
  BROWSER_CMD="npm --prefix app/ui run test:e2e"
  BROWSER_OUTPUT=""
  BROWSER_EXIT=0
  run_captured_command BROWSER_OUTPUT "$BROWSER_CMD" || BROWSER_EXIT=$?

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
