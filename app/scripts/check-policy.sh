#!/usr/bin/env bash
set -uo pipefail

# Policy sync note: keep AGENTS.md schema workspace-state entries aligned with backend/database.py,
# including dedicated tool_configs and connector_auth_policies ownership when present, plus connector
# storage ownership notes when policy text changes around runtime-vs-migration source of truth.
# Note: updated to reflect factoring/fix-first/source-of-truth wording plus
# startup-only connector legacy migration, workflow-builder service-only sync checks,
# and Trello OAuth connector policy sync notes on 2026-04-04.
# TASK-019 (2026-04-05): added PR-scope validator hook (scripts/check-pr-scope.sh);
# rule-ID cross-references added to Required Workflow, Implementation Quality, and domain AGENTS files;
# Practical Do And Do Not section restructured with rule annotations.
# TASK-023 (2026-04-06): module-contract process retired; canonical documentation model
# is limited to tasks, AGENTS policy files, README, and docs (R-DOC-001).
# TASK-024 (2026-04-07): task-file construction is canonical in AGENTS.md; task-builder
# must defer to AGENTS for documentation/testing/github rules, keep mandatory Test impact
# review, and avoid a separate Documentation review section.
# TASK-025 (2026-04-10): audit policy clarified that `[AREA: audit]` work must keep
# named scopes and current batches explicit in `.github/repo-scan-index.md`; repo-scan
# shape checks continue to require the dedicated `scope` and `notes` columns.
# TASK-026 (2026-04-11): startup lifecycle policy now requires real launcher coverage
# in app/tests/test_startup_lifecycle.py and failure-log capture to data/logs/.
# TASK-027 (2026-04-11): real-test-runner first-pass policy (R-TEST-009) added;
# test-real-failfast.sh is the canonical first-pass AI command; stubbed Playwright
# coverage is secondary for critical workflow verification.
# TASK-027 step 4: test-precommit.sh now invokes test-real-failfast.sh as its first step
# before adding coverage and UI gate checks; R-TEST-002 description updated to match.

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="$ROOT_DIR/app"
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
      app/ui/dist/*|app/ui/node_modules/*|node_modules/*)
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
  if path_changed "AGENTS.md" && ! path_changed "app/scripts/check-policy.sh"; then
    printf 'AGENTS.md changed without a matching update to app/scripts/check-policy.sh.\n'
    return 1
  fi

  printf 'AGENTS.md and app/scripts/check-policy.sh are aligned for this change.\n'
}

check_documentation_ownership_model() {
  local missing=()

  if [[ ! -f "AGENTS.md" ]]; then
    printf 'Missing AGENTS.md; cannot validate documentation ownership model.\n'
    return 1
  fi

  if [[ ! -f "README.md" ]]; then
    printf 'Missing README.md; cannot validate documentation ownership model.\n'
    return 1
  fi

  if ! grep -q "## Documentation Ownership Model" AGENTS.md; then
    missing+=("AGENTS.md: ## Documentation Ownership Model")
  fi

  if ! grep -q "R-DOC-001" AGENTS.md; then
    missing+=("AGENTS.md: R-DOC-001 rules matrix entry")
  fi

  if ! grep -q "## Documentation Ownership" README.md; then
    missing+=("README.md: ## Documentation Ownership")
  fi

  if [[ -d ".agents/module-contracts" ]]; then
    missing+=(".agents/module-contracts directory must be retired")
  fi

  if [[ -d ".agents" ]] && [[ -d ".agents"/"tasks" ]]; then
    missing+=("Legacy tasks directory must be retired after migration to .github/tasks")
  fi

  if [[ ! -d ".github/tasks/open" ]]; then
    missing+=(".github/tasks/open directory is required for active task tracking")
  fi

  if [[ ! -d ".github/tasks/closed" ]]; then
    missing+=(".github/tasks/closed directory is required for closed task history")
  fi

  if ((${#missing[@]} > 0)); then
    printf 'Documentation ownership model checks failed:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Documentation ownership model is explicit and no module-contract system is active.\n'
}

check_task_file_policy_sync() {
  local missing=()
  local agents_file="AGENTS.md"
  local builder_file=".github/agents/task-builder.md"

  if [[ ! -f "$agents_file" ]]; then
    printf 'Missing AGENTS.md; cannot validate task file policy.\n'
    return 1
  fi

  if [[ ! -f "$builder_file" ]]; then
    printf 'Missing task-builder agent file: %s\n' "$builder_file"
    return 1
  fi

  if ! grep -q "## Task File Construction" "$agents_file"; then
    missing+=("AGENTS.md: ## Task File Construction")
  fi

  if ! grep -q "R-TASK-001" "$agents_file"; then
    missing+=("AGENTS.md: R-TASK-001 rules matrix entry")
  fi

  if ! grep -q "R-TASK-002" "$agents_file"; then
    missing+=("AGENTS.md: R-TASK-002 rules matrix entry")
  fi

  if ! grep -q '^3\. `Testing`$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: Required Task File Structure must include section 3 as `Testing`")
  fi

  if ! grep -q '^4\. `GitHub update`$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: Required Task File Structure must include section 4 as `GitHub update`")
  fi

  if grep -q '^4\. `Documentation review`$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: Documentation review section must not be required")
  fi

  if grep -q '^## Documentation Review Rules$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: duplicate Documentation Review Rules section must be removed")
  fi

  if grep -q '^## Testing Step Rules$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: duplicate Testing Step Rules section must be removed")
  fi

  if grep -q '^## GitHub Update Rules$' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: duplicate GitHub Update Rules section must be removed")
  fi

  if ! grep -q 'AGENTS.md#task-file-construction' "$builder_file"; then
    missing+=(".github/agents/task-builder.md: AGENTS.md#task-file-construction reference")
  fi

  if ((${#missing[@]} > 0)); then
    printf 'Task file policy sync checks failed:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Task file construction is canonical in AGENTS.md and task-builder defers to that policy.\n'
}

check_startup_launcher_policy_sync() {
  local tests_agents_file="app/tests/AGENTS.md"
  local missing=()

  if [[ ! -f "$tests_agents_file" ]]; then
    printf 'Missing %s; cannot validate startup launcher policy sync.\n' "$tests_agents_file"
    return 1
  fi

  if ! grep -q "real uvicorn startup process" "$tests_agents_file"; then
    missing+=("app/tests/AGENTS.md: startup policy must require a real uvicorn startup process test")
  fi

  if ! grep -q 'captures stdout/stderr output to `data/logs/`' "$tests_agents_file"; then
    missing+=("app/tests/AGENTS.md: startup policy must require failure output capture to data/logs/")
  fi

  if ! grep -q "R-TEST-007" AGENTS.md; then
    missing+=("AGENTS.md: R-TEST-007 rules matrix entry")
  fi

  if ((${#missing[@]} > 0)); then
    printf 'Startup launcher policy sync checks failed:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Startup launcher policy text is synchronized across AGENTS.md and app/tests/AGENTS.md.\n'
}

check_real_test_failfast_policy_sync() {
  local missing=()

  if ! grep -q "test-real-failfast.sh" AGENTS.md; then
    missing+=("AGENTS.md: must reference app/scripts/test-real-failfast.sh as the first-pass AI command")
  fi

  if ! grep -q "Real-Test First-Pass Policy" AGENTS.md; then
    missing+=("AGENTS.md: must contain a ## Real-Test First-Pass Policy section")
  fi

  if ! grep -q "R-TEST-009" AGENTS.md; then
    missing+=("AGENTS.md: R-TEST-009 rules matrix entry")
  fi

  if ! grep -q "test-real-failfast.sh" "app/tests/AGENTS.md"; then
    missing+=("app/tests/AGENTS.md: must reference app/scripts/test-real-failfast.sh")
  fi

  if ! grep -q "test-real-failfast.sh" "app/ui/e2e/README.md"; then
    missing+=("app/ui/e2e/README.md: must reference app/scripts/test-real-failfast.sh")
  fi

  if ((${#missing[@]} > 0)); then
    printf 'Real-test first-pass policy sync checks failed:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Real-test first-pass policy is synchronized across AGENTS.md, app/tests/AGENTS.md, and app/ui/e2e/README.md.\n'
}

check_db_schema_docs_sync() {
  local missing=()

  if ! path_changed "app/backend/database.py"; then
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
    printf 'app/backend/database.py changed without updating schema documentation in:\n'
    printf '  %s\n' "${missing[@]}"
    return 1
  fi

  printf 'Schema source changes include AGENTS.md and README.md updates.\n'
}

check_policy_family_review() {
  local changed_policy_files=()
  local policy_file

  for policy_file in AGENTS.md app/backend/AGENTS.md app/ui/AGENTS.md app/tests/AGENTS.md; do
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

check_repo_scan_index_shape() {
  local tracker_file=".github/repo-scan-index.md"
  local missing_markers=()
  local marker

  if [[ ! -f "$tracker_file" ]]; then
    printf 'Missing repo audit tracker: %s\n' "$tracker_file"
    return 1
  fi

  for marker in \
    "^# Repo Scan Index$" \
    "^## Status Keys$" \
    "^## Index$" \
    "^\\| path \\| status \\| last_reviewed \\| scope \\| notes \\|$" \
    '`pending`' \
    '`in_progress`' \
    '`reviewed`' \
    '`needs_followup`' \
    '`blocked`' \
    '`skip_generated`'
  do
    if ! grep -q "$marker" "$tracker_file"; then
      missing_markers+=("$marker")
    fi
  done

  if ((${#missing_markers[@]} > 0)); then
    printf 'Repo audit tracker is missing required markers:\n'
    printf '  %s\n' "${missing_markers[@]}"
    return 1
  fi

  printf 'Repo audit tracker exists and includes the required status, scope, and notes shape.\n'
}

check_tool_manifest_sync() {
  local catalog_diff=""

  if ! path_changed "app/backend/tool_registry.py"; then
    printf 'No tool catalog definition changes detected.\n'
    return 0
  fi

  catalog_diff="$(git diff -- app/backend/tool_registry.py)"
  if ! printf '%s' "$catalog_diff" | rg -q '^[+-].*(DEFAULT_TOOL_CATALOG|"id":|"name":|"description":|"inputs":|"outputs":)'; then
    printf 'No tool catalog definition changes detected.\n'
    return 0
  fi

  if ! path_changed "app/ui/scripts/tools-manifest.js"; then
    printf 'app/backend/tool_registry.py changed without regenerating app/ui/scripts/tools-manifest.js.\n'
    return 1
  fi

  printf 'Tool catalog changes include the regenerated manifest.\n'
}

check_workflow_builder_connector_path_sync() {
  local service_changed=0
  local route_changed=0
  local ui_changed=0
  local builder_tests_changed=0

  path_changed "app/backend/services/workflow_builder.py" && service_changed=1
  path_changed "app/backend/routes/automations.py" && route_changed=1
  path_changed "app/ui/src/automation/app.tsx" && ui_changed=1
  if path_changed "app/tests/test_connectors_for_builder.py" || path_changed "app/tests/test_connectors_for_builder_extra.py"; then
    builder_tests_changed=1
  fi

  if ((service_changed == 0 && route_changed == 0 && ui_changed == 0 && builder_tests_changed == 0)); then
    printf 'No workflow-builder connector source-of-truth files changed.\n'
    return 0
  fi

  if ((route_changed == 1)) && ((ui_changed == 0)); then
    printf 'Workflow connector backend path changed without updating app/ui/src/automation/app.tsx consumer.\n'
    return 1
  fi

  if ((service_changed == 1)) && ((route_changed == 0)) && ((ui_changed == 0)); then
    printf 'Workflow-builder connector service changed without route/UI changes; consumer contract is assumed unchanged and should be covered by builder tests.\n'
    return 0
  fi

  printf 'Workflow-builder connector source-of-truth path remains synchronized (persisted connectors via backend resolver).\n'
}

check_connector_route_service_boundary() {
  local route_file="app/backend/routes/connectors.py"
  local boundary_violations=()

  if [[ ! -f "$route_file" ]]; then
    printf 'Missing route file: %s\n' "$route_file"
    return 1
  fi

  if rg -n '^def (_exchange_[a-z0-9_]+_oauth_code_for_tokens|_refresh_[a-z0-9_]+_access_token|_revoke_[a-z0-9_]+_token)\(' "$route_file" >/dev/null; then
    boundary_violations+=("$route_file defines provider-specific OAuth token lifecycle helpers")
  fi

  if rg -n '^from backend\.routes\.connectors import ' app/backend/services/support.py app/backend/services/connector_oauth.py >/dev/null; then
    boundary_violations+=("backend services import connector route helpers as business-logic dependencies")
  fi

  if ((${#boundary_violations[@]} > 0)); then
    printf 'Connector route/service boundary violations detected:\n'
    printf '  %s\n' "${boundary_violations[@]}"
    return 1
  fi

  printf 'Connector OAuth lifecycle handlers stay in backend services and route glue remains thin.\n'
}

check_large_changed_source_files() {
  local threshold=600
  local file
  local line_count
  local flagged=()

  for file in "${CHANGED_FILES[@]:-}"; do
    [[ -f "$file" ]] || continue

    case "$file" in
      AGENTS.md|app/backend/AGENTS.md|app/ui/AGENTS.md|app/tests/AGENTS.md|app/scripts/check-policy.sh)
        continue
        ;;
      app/backend/*.py|app/backend/**/*.py|app/ui/src/*.ts|app/ui/src/*.tsx|app/ui/src/**/*.ts|app/ui/src/**/*.tsx|app/ui/scripts/*.js|app/ui/scripts/**/*.js|app/tests/*.py|app/tests/**/*.py)
        ;;
      *)
        continue
        ;;
    esac

    line_count="$(wc -l < "$file" | tr -d ' ')"
    if [[ "$line_count" -gt "$threshold" ]]; then
      flagged+=("$file ($line_count lines)")
    fi
  done

  if ((${#flagged[@]} == 0)); then
    printf 'No changed source files exceed %d lines.\n' "$threshold"
    return 0
  fi

  printf 'Changed source files exceeding %d lines were detected and should be reviewed for factoring:\n' "$threshold"
  printf '  %s\n' "${flagged[@]}"
  print_warn "Oversized changed source files require a factoring sanity check."
}

check_pr_scope() {
  if [[ ! -x "$APP_DIR/scripts/check-pr-scope.sh" ]]; then
    printf 'app/scripts/check-pr-scope.sh not found or not executable; skipping PR scope check.\n'
    return 0
  fi
  "$APP_DIR/scripts/check-pr-scope.sh"
}

check_test_precommit() {
  "$APP_DIR/scripts/test-precommit.sh"
}

check_test_full() {
  "$APP_DIR/scripts/test-full.sh"
}

collect_changed_files

if ((${#CHANGED_FILES[@]} > 0)); then
  printf 'Inspecting %d changed file(s).\n' "${#CHANGED_FILES[@]}"
else
  printf 'No changed files detected. Path-based checks are running against the current clean tree or last commit.\n'
fi

run_check "Forbidden path modifications" check_forbidden_path_modifications
run_check "AGENTS/check-policy sync" check_agents_script_sync
run_check "Documentation ownership model" check_documentation_ownership_model
run_check "Task file policy sync" check_task_file_policy_sync
run_check "Startup launcher policy sync" check_startup_launcher_policy_sync
run_check "Real-test first-pass policy sync" check_real_test_failfast_policy_sync
run_check "DB schema documentation sync" check_db_schema_docs_sync
run_warning_check "Policy file review coverage" check_policy_family_review
run_check "Repo scan index shape" check_repo_scan_index_shape
run_check "Tool manifest regeneration" check_tool_manifest_sync
run_check "Workflow builder connector path sync" check_workflow_builder_connector_path_sync
run_check "Connector route/service boundary" check_connector_route_service_boundary
run_warning_check "Large changed source files" check_large_changed_source_files
run_warning_check "PR scope validation" check_pr_scope
run_check "app/scripts/test-precommit.sh" check_test_precommit
run_check "app/scripts/test-full.sh" check_test_full

printf '\nSummary: %d failure(s), %d warning(s).\n' "$FAILURES" "$WARNINGS"

if ((FAILURES > 0)); then
  exit 1
fi

exit 0
