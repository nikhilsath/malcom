#!/usr/bin/env bash
# test-real-failfast.sh — AI agent first-pass command.
#
# This script delegates to test-system.sh, which builds the test environment
# from scratch (bootstrap → db_setup → startup_lifecycle → backend_suite) and
# stops on the first failure.  The machine-readable artifact is written to
# app/tests/test-artifacts/system-result.json and mirrored to the legacy path
# failfast-result.json for backward compatibility with any tooling that reads
# the older location.
#
# Agents and CI should prefer running this script directly per R-TEST-009.
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

ARTIFACT_DIR="app/tests/test-artifacts"
SYSTEM_ARTIFACT="$ARTIFACT_DIR/system-result.json"
LEGACY_ARTIFACT="$ARTIFACT_DIR/failfast-result.json"

# Delegate all environment-building and test execution to test-system.sh.
bash app/scripts/test-system.sh "$@"
EXIT_CODE=$?

# Mirror the artifact to the legacy failfast path for backward compatibility.
if [[ -f "$SYSTEM_ARTIFACT" ]]; then
  cp "$SYSTEM_ARTIFACT" "$LEGACY_ARTIFACT"
fi

exit "$EXIT_CODE"
