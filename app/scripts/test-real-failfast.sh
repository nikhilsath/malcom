#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

ARTIFACT_DIR="app/tests/test-artifacts"
ARTIFACT_FILE="$ARTIFACT_DIR/failfast-result.json"
mkdir -p "$ARTIFACT_DIR"

# Step 1: PostgreSQL preflight
PREFLIGHT_CMD=".venv/bin/python app/scripts/require_test_database.py"
PREFLIGHT_OUTPUT=$(eval "$PREFLIGHT_CMD" 2>&1) || PREFLIGHT_EXIT=$?
PREFLIGHT_EXIT=${PREFLIGHT_EXIT:-0}

if [[ "$PREFLIGHT_EXIT" -ne 0 ]]; then
  echo "PostgreSQL preflight failed"
  FIRST_ERROR_LINES=$(echo "$PREFLIGHT_OUTPUT" | tail -40 | python3 -c "import sys,json; lines=sys.stdin.read().splitlines(); print(json.dumps(lines))")
  python3 -c "
import json
data = {
    'step': 'preflight',
    'exit_code': $PREFLIGHT_EXIT,
    'command': '$PREFLIGHT_CMD',
    'first_error_lines': $FIRST_ERROR_LINES
}
with open('$ARTIFACT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
  exit 1
fi

# Step 2: Startup/backup lifecycle tests (highest-value real tests first)
LIFECYCLE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short app/tests/test_startup_lifecycle.py"
LIFECYCLE_OUTPUT=$(eval "$LIFECYCLE_CMD" 2>&1) || LIFECYCLE_EXIT=$?
LIFECYCLE_EXIT=${LIFECYCLE_EXIT:-0}

if [[ "$LIFECYCLE_EXIT" -ne 0 ]]; then
  FIRST_ERROR_LINES=$(echo "$LIFECYCLE_OUTPUT" | tail -40 | python3 -c "import sys,json; lines=sys.stdin.read().splitlines(); print(json.dumps(lines))")
  python3 -c "
import json
data = {
    'step': 'startup_lifecycle',
    'exit_code': $LIFECYCLE_EXIT,
    'command': '$LIFECYCLE_CMD',
    'first_error_lines': $FIRST_ERROR_LINES
}
with open('$ARTIFACT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
  exit 1
fi

# Step 3: Full real-test suite (fail on first failure, exclude smoke)
SUITE_CMD=".venv/bin/pytest -c app/pytest.ini -x -q --tb=short -m \"not smoke\" app/tests/"
SUITE_OUTPUT=$(eval "$SUITE_CMD" 2>&1) || SUITE_EXIT=$?
SUITE_EXIT=${SUITE_EXIT:-0}

if [[ "$SUITE_EXIT" -ne 0 ]]; then
  FIRST_ERROR_LINES=$(echo "$SUITE_OUTPUT" | tail -40 | python3 -c "import sys,json; lines=sys.stdin.read().splitlines(); print(json.dumps(lines))")
  python3 -c "
import json
data = {
    'step': 'backend_suite',
    'exit_code': $SUITE_EXIT,
    'command': '$SUITE_CMD',
    'first_error_lines': $FIRST_ERROR_LINES
}
with open('$ARTIFACT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
  exit 1
fi

# All real tests passed
python3 -c "
import json
data = {
    'step': 'all',
    'exit_code': 0,
    'command': 'test-real-failfast.sh',
    'first_error_lines': []
}
with open('$ARTIFACT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
echo "All real tests passed."
