#!/usr/bin/env bash
set -uo pipefail

# Policy sync note: keep AGENTS.md schema workspace-state entries aligned with backend/database.py.
# Note: updated to reflect workflow storage documentation (data.workflow_storage_path) on 2026-03-29.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

FAILURES=0
WARNINGS=0
declare -a CHANGED_FILES=()

print_check() {
  printf '\n==> %s\n' "$1"
}

print_pass() {
  printf 'PASS: %s\n' "$1"
}

print_warn() {
  printf 'WARN: %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

print_fail() {
  printf 'FAIL: %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

collect_changed_files() {
  local diff_output=""
  local line

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    if git diff --quiet HEAD -- && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
      if git rev-parse --verify HEAD^ >/dev/null 2>&1; then
        diff_output="$(git diff --name-only HEAD^ HEAD)"
      fi
    else
      diff_output="$(
        {
          git diff --name-only HEAD
          git ls-files --others --exclude-standard
        } | awk 'NF' | sort -u
      )"
    fi
  else
    diff_output="$(
      {
        git diff --name-only --cached
        git ls-files --others --exclude-standard
      } | awk 'NF' | sort -u
    )"
  fi

  if [[ -n "$diff_output" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      CHANGED_FILES+=("$line")
    done <<<"$diff_output"
  fi
}

path_changed() {
  local target="$1"
  local file

  for file in "${CHANGED_FILES[@]:-}"; do
    if [[ "$file" == "$target" ]]; then
      return 0
    fi
  done

  return 1
}

run_check() {
  local label="$1"
  local function_name="$2"

  print_check "$label"
  if "$function_name"; then
    print_pass "$label"
  else
    print_fail "$label"
  fi
}

run_warning_check() {
  local label="$1"
  local function_name="$2"

  print_check "$label"
  "$function_name"
  print_pass "$label"
}

check_forbidden_path_modifications() {
  local forbidden=()
  local file

  for file in "${CHANGED_FILES[@]:-}"; do
    case "$file" in
      ui/dist/*|ui/node_modules/*|node_modules/*)
        forbidden+=("$file")
        ;;
    esac
  done

  if ((${#forbidden[@]} > 0)); then
    printf 'Forbidden generated/runtime paths were modified:\n'
    printf '  %s\n' "${forbidden[@]}"
    return 1
  fi

  printf 'No forbidden generated/runtime paths are modified.\n'
}

check_agents_script_sync() {
  if path_changed "AGENTS.md" && ! path_changed "scripts/check-policy.sh"; then
    printf 'AGENTS.md changed without a matching update to scripts/check-policy.sh.\n'
    return 1
  fi

  printf 'AGENTS.md and scripts/check-policy.sh are aligned for this change.\n'
}

check_db_schema_docs_sync() {
  local missing=()

  if ! path_changed "backend/database.py"; then
    printf 'No schema source changes detected.\n'
    return 0
  fi

  if ! path_changed "AGENTS.md"; then
    missing+=("AGENTS.md")
  fi

  if ! path_changed "README.md"; then
    missing+=("README.md")
  fi

  if ((${#missing[@]} > 0)); then
    printf 'backend/database.py changed without updating schema documentation in:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Schema source changes include AGENTS.md and README.md updates.\n'
}

check_policy_family_review() {
  local changed_policy_files=()
  local policy_file

  for policy_file in AGENTS.md backend/AGENTS.md ui/AGENTS.md tests/AGENTS.md; do
    if path_changed "$policy_file"; then
      changed_policy_files+=("$policy_file")
    fi
  done

  if ((${#changed_policy_files[@]} == 0)); then
    printf 'No policy files changed.\n'
    return 0
  fi

  printf 'Policy files changed:\n'
  printf '  %s\n' "${changed_policy_files[@]}"

  if ! path_changed "AGENTS.md"; then
    print_warn "Domain policy files changed without AGENTS.md. Confirm the root policy still matches."
  fi
}

check_tool_manifest_sync() {
  if ! path_changed "backend/tool_registry.py"; then
    printf 'No tool catalog definition changes detected.\n'
    return 0
  fi

  if ! path_changed "ui/scripts/tools-manifest.js"; then
    printf 'backend/tool_registry.py changed without regenerating ui/scripts/tools-manifest.js.\n'
    return 1
  fi

  printf 'Tool catalog changes include the regenerated manifest.\n'
}

check_workflow_builder_connector_path_sync() {
  local service_changed=0
  local route_changed=0
  local ui_changed=0

  path_changed "backend/services/workflow_builder.py" && service_changed=1
  path_changed "backend/routes/automations.py" && route_changed=1
  path_changed "ui/src/automation/app.tsx" && ui_changed=1

  if ((service_changed == 0 && route_changed == 0 && ui_changed == 0)); then
    printf 'No workflow-builder connector source-of-truth files changed.\n'
    return 0
  fi

  if ((service_changed == 1 || route_changed == 1)) && ((ui_changed == 0)); then
    printf 'Workflow connector backend path changed without updating ui/src/automation/app.tsx consumer.\n'
    return 1
  fi

  printf 'Workflow-builder connector source-of-truth path remains synchronized.\n'
}

check_test_precommit() {
  "$ROOT_DIR/scripts/test-precommit.sh"
}

check_test_full() {
  "$ROOT_DIR/scripts/test-full.sh"
}

collect_changed_files

if ((${#CHANGED_FILES[@]} > 0)); then
  printf 'Inspecting %d changed file(s).\n' "${#CHANGED_FILES[@]}"
else
  printf 'No changed files detected. Path-based checks are running against the current clean tree or last commit.\n'
fi

run_check "Forbidden path modifications" check_forbidden_path_modifications
run_check "AGENTS/check-policy sync" check_agents_script_sync
run_check "DB schema documentation sync" check_db_schema_docs_sync
run_warning_check "Policy file review coverage" check_policy_family_review
run_check "Tool manifest regeneration" check_tool_manifest_sync
run_check "Workflow builder connector path sync" check_workflow_builder_connector_path_sync
run_check "scripts/test-precommit.sh" check_test_precommit
run_check "scripts/test-full.sh" check_test_full

printf '\nSummary: %d failure(s), %d warning(s).\n' "$FAILURES" "$WARNINGS"

if ((FAILURES > 0)); then
  exit 1
fi

exit 0
