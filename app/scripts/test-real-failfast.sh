#!/usr/bin/env bash
# test-real-failfast.sh — AI agent first-pass command.
#
# This script delegates to test-system.sh, which builds the test environment
# from scratch (bootstrap → db_setup → startup_lifecycle → backend_suite) and
# stops on the first failure. The machine-readable artifact is written to
# app/tests/test-artifacts/system-result.json.
#
# Agents and CI should prefer running this script directly per R-TEST-009.
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

ARTIFACT_DIR="${MALCOM_TEST_ARTIFACT_DIR:-app/tests/test-artifacts}"
SYSTEM_ARTIFACT="$ARTIFACT_DIR/system-result.json"
mkdir -p "$ARTIFACT_DIR"

# Only the canonical system-result artifact is supported now; drop any stale
# legacy mirror so callers never read an outdated fallback path by accident.
rm -f "$ARTIFACT_DIR/failfast-result.json"

bash app/scripts/test-system.sh "$@" || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}

if [[ "$EXIT_CODE" -ne 0 && ! -f "$SYSTEM_ARTIFACT" ]]; then
  echo "test-real-failfast.sh expected $SYSTEM_ARTIFACT after test-system.sh failure" >&2
fi

exit "$EXIT_CODE"
