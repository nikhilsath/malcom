#!/usr/bin/env bash
# check-pr-scope.sh — PR scope validation (dry-run / advisory)
#
# Checks that a PR does not inadvertently mix unrelated concerns.
# Runs in advisory mode: violations are printed as warnings, not hard failures.
# Wire this into check-policy.sh or pre-merge CI as needed.
#
# Exit codes: 0 = pass (clean or advisory warnings only), 1 = hard failure
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$WORKSPACE_ROOT"

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

# Rule: schema changes must not silently mix into unrelated feature PRs.
check_schema_change_isolation() {
  if ! any_changed_matching "app/backend/database.py"; then
    printf 'No schema changes detected.\n'
    return 0
  fi

  # Check that migration files are also present
  local migration_added=0
  local file
  for file in "${CHANGED_FILES[@]:-}"; do
    if [[ "$file" == app/backend/migrations/versions/*.py ]]; then
      migration_added=1
      break
    fi
  done

  if ((migration_added == 0)); then
    print_warn "app/backend/database.py changed without a matching migration in app/backend/migrations/versions/. Confirm whether a migration is needed."
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
      app/ui/dist/*)
        generated+=("$file")
        ;;
      app/backend/*.py|app/ui/src/*.ts|app/ui/src/*.tsx|app/ui/scripts/*.js)
        source_touched=1
        ;;
    esac
  done

  if ((${#generated[@]} > 0)) && ((source_touched == 1)); then
    printf 'Generated output files committed alongside source files:\n'
    printf '  %s\n' "${generated[@]}"
    print_fail "Do not commit app/ui/dist/** files. They are build artifacts."
    return 1
  fi

  printf 'No mixed generated/source commits detected.\n'
}

# Rule: connector route boundary — no provider OAuth lifecycle helpers in the route file.
# (This duplicates the hard check in check-policy.sh; here it is an advisory pre-check.)
check_connector_route_boundary_advisory() {
  local route_file="app/backend/routes/connectors.py"
  if [[ ! -f "$route_file" ]]; then
    printf 'Route file not found; skipping.\n'
    return 0
  fi

  if rg -n '^def (_exchange_[a-z0-9_]+_oauth_code_for_tokens|_refresh_[a-z0-9_]+_access_token|_revoke_[a-z0-9_]+_token)\(' "$route_file" >/dev/null 2>&1; then
    print_warn "Provider-specific OAuth lifecycle helpers detected in $route_file. Move them to app/backend/services/connector_oauth.py (R-CONN-005)."
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
