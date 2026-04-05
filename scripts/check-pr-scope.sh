#!/usr/bin/env bash
# check-pr-scope.sh — PR scope validation (dry-run / advisory)
#
# Checks that a PR does not inadvertently mix unrelated concerns.
# Runs in advisory mode: violations are printed as warnings, not hard failures.
# Wire this into check-policy.sh or pre-merge CI as needed.
#
# Exit codes: 0 = pass (clean or advisory warnings only), 1 = hard failure
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

WARNINGS=0
FAILURES=0

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

# ---------------------------------------------------------------------------
# Collect changed files (same logic as check-policy.sh)
# ---------------------------------------------------------------------------
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

any_changed_matching() {
  local pattern="$1"
  local file
  for file in "${CHANGED_FILES[@]:-}"; do
    if [[ "$file" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

# ---------------------------------------------------------------------------
# Scope checks
# ---------------------------------------------------------------------------

# Rule: extraction PRs (modularisation work) must include a module contract.
check_extraction_has_contract() {
  local new_service_files=()
  local file

  for file in "${CHANGED_FILES[@]:-}"; do
    case "$file" in
      backend/services/*.py|ui/src/*/index.ts|ui/src/*/index.tsx)
        # Skip files that already exist (not net-new) by checking git status
        if git diff --name-only HEAD -- "$file" 2>/dev/null | grep -q "$file"; then
          # file was modified, not added — skip
          :
        elif git ls-files --others --exclude-standard "$file" 2>/dev/null | grep -q "$file"; then
          new_service_files+=("$file")
        elif git diff --name-only --diff-filter=A HEAD -- "$file" 2>/dev/null | grep -q "$file"; then
          new_service_files+=("$file")
        fi
        ;;
    esac
  done

  if ((${#new_service_files[@]} == 0)); then
    printf 'No new service/module files detected; contract check skipped.\n'
    return 0
  fi

  local contract_added=0
  for file in "${CHANGED_FILES[@]:-}"; do
    if [[ "$file" == .agents/module-contracts/*.md ]]; then
      contract_added=1
      break
    fi
  done

  if ((contract_added == 0)); then
    printf 'New service/module files were added without a module contract:\n'
    printf '  %s\n' "${new_service_files[@]}"
    print_warn "Add a contract file under .agents/module-contracts/<module-name>.md"
    return 0  # advisory only
  fi

  printf 'New module file(s) accompanied by a module contract. OK.\n'
}

# Rule: schema changes must not silently mix into unrelated feature PRs.
check_schema_change_isolation() {
  if ! any_changed_matching "backend/database.py"; then
    printf 'No schema changes detected.\n'
    return 0
  fi

  # Check that migration files are also present
  local migration_added=0
  local file
  for file in "${CHANGED_FILES[@]:-}"; do
    if [[ "$file" == backend/migrations/versions/*.py ]]; then
      migration_added=1
      break
    fi
  done

  if ((migration_added == 0)); then
    print_warn "backend/database.py changed without a matching migration in backend/migrations/versions/. Confirm whether a migration is needed."
  else
    printf 'Schema change accompanied by a migration file. OK.\n'
  fi
}

# Rule: generated files must not be committed alongside hand-edited source.
check_no_mixed_generated_source() {
  local generated=()
  local source_touched=0
  local file

  for file in "${CHANGED_FILES[@]:-}"; do
    case "$file" in
      ui/dist/*)
        generated+=("$file")
        ;;
      backend/*.py|ui/src/*.ts|ui/src/*.tsx|ui/scripts/*.js)
        source_touched=1
        ;;
    esac
  done

  if ((${#generated[@]} > 0)) && ((source_touched == 1)); then
    printf 'Generated output files committed alongside source files:\n'
    printf '  %s\n' "${generated[@]}"
    print_fail "Do not commit ui/dist/** files. They are build artifacts."
    return 1
  fi

  printf 'No mixed generated/source commits detected.\n'
}

# Rule: connector route boundary — no provider OAuth lifecycle helpers in the route file.
# (This duplicates the hard check in check-policy.sh; here it is an advisory pre-check.)
check_connector_route_boundary_advisory() {
  local route_file="backend/routes/connectors.py"
  if [[ ! -f "$route_file" ]]; then
    printf 'Route file not found; skipping.\n'
    return 0
  fi

  if rg -n '^def (_exchange_[a-z0-9_]+_oauth_code_for_tokens|_refresh_[a-z0-9_]+_access_token|_revoke_[a-z0-9_]+_token)\(' "$route_file" >/dev/null 2>&1; then
    print_warn "Provider-specific OAuth lifecycle helpers detected in $route_file. Move them to backend/services/connector_oauth.py (R-CONN-005)."
  else
    printf 'Connector route boundary looks clean (R-CONN-005).\n'
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
collect_changed_files

if ((${#CHANGED_FILES[@]} > 0)); then
  printf 'PR scope check: inspecting %d changed file(s).\n' "${#CHANGED_FILES[@]}"
else
  printf 'No changed files detected; running checks against current tree.\n'
fi

print_check "New module contract presence"
check_extraction_has_contract

print_check "Schema change isolation"
check_schema_change_isolation

print_check "No mixed generated/source commits"
if ! check_no_mixed_generated_source; then
  : # failure already recorded
fi

print_check "Connector route boundary (advisory)"
check_connector_route_boundary_advisory

printf '\nPR scope summary: %d failure(s), %d warning(s).\n' "$FAILURES" "$WARNINGS"

if ((FAILURES > 0)); then
  exit 1
fi

exit 0
