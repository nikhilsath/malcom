#!/usr/bin/env bash
# test-module.sh — run unit and/or contract tests for a named module.
#
# Usage:
#   scripts/test-module.sh <module-name> [--unit | --contract | --all]
#
# <module-name> must correspond to:
#   - a Python module:   tests/unit/test_<module-name>.py  (unit)
#                        tests/contract/test_<module-name>_contract.py  (contract)
#   - a UI module:       ui/src/<module-name>/__tests__/  (unit)
#                        ui/e2e/<module-name>.spec.ts  (e2e/contract)
#
# Flags:
#   --unit      run only unit tests (default when no flag is given)
#   --contract  run only contract tests
#   --all       run unit + contract tests
#
# Exit codes: 0 = all selected tiers pass, 1 = at least one tier failed.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODULE="${1:-}"
TIER="${2:---unit}"

if [[ -z "$MODULE" ]]; then
  printf 'Usage: %s <module-name> [--unit | --contract | --all]\n' "$0" >&2
  exit 1
fi

FAILURES=0

run_tier() {
  local tier="$1"
  local description="$2"
  local cmd=("${@:3}")

  printf '\n==> %s (%s)\n' "$description" "$MODULE"
  if "${cmd[@]}"; then
    printf 'PASS: %s\n' "$description"
  else
    printf 'FAIL: %s\n' "$description"
    FAILURES=$((FAILURES + 1))
  fi
}

run_python_unit() {
  local unit_file="tests/unit/test_${MODULE}.py"
  if [[ ! -f "$unit_file" ]]; then
    printf 'SKIP: %s not found\n' "$unit_file"
    return 0
  fi
  run_tier "unit" "Python unit tests" python3 -m pytest "$unit_file" -q
}

run_python_contract() {
  local contract_file="tests/contract/test_${MODULE}_contract.py"
  if [[ ! -f "$contract_file" ]]; then
    printf 'SKIP: %s not found\n' "$contract_file"
    return 0
  fi
  run_tier "contract" "Python contract tests" python3 -m pytest "$contract_file" -q
}

run_ui_unit() {
  local ui_test_dir="ui/src/${MODULE}/__tests__"
  if [[ ! -d "$ui_test_dir" ]]; then
    printf 'SKIP: %s not found\n' "$ui_test_dir"
    return 0
  fi
  run_tier "unit" "UI unit tests" bash -c "cd ui && npm test -- --testPathPattern='src/${MODULE}/__tests__' --passWithNoTests"
}

run_ui_e2e() {
  local e2e_spec="ui/e2e/${MODULE}.spec.ts"
  if [[ ! -f "$e2e_spec" ]]; then
    printf 'SKIP: %s not found\n' "$e2e_spec"
    return 0
  fi
  run_tier "e2e" "Playwright e2e tests" bash -c "cd ui && npx playwright test e2e/${MODULE}.spec.ts"
}

case "$TIER" in
  --unit)
    run_python_unit
    run_ui_unit
    ;;
  --contract)
    run_python_contract
    run_ui_e2e
    ;;
  --all)
    run_python_unit
    run_python_contract
    run_ui_unit
    run_ui_e2e
    ;;
  *)
    printf 'Unknown flag: %s\n' "$TIER" >&2
    printf 'Usage: %s <module-name> [--unit | --contract | --all]\n' "$0" >&2
    exit 1
    ;;
esac

printf '\nModule test summary for "%s": %d failure(s).\n' "$MODULE" "$FAILURES"

if ((FAILURES > 0)); then
  exit 1
fi

exit 0
