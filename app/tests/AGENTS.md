# app/tests/AGENTS.md

Root policy remains authoritative in AGENTS.md.
This file defines testing and verification rules and should be read after root routing.

## Scope

Applies to backend tests, frontend tests, Playwright workflow coverage, smoke matrix obligations, and startup triage for test execution blockers.

---

## Testing And Verification

> Rule IDs from root policy: R-TEST-001 through R-TEST-008. See [../AGENTS.md#rules-matrix](../AGENTS.md#rules-matrix) for full definitions.

Every meaningful code change should include the smallest relevant verification set.

Build tests as implementation progresses rather than deferring all coverage to a follow-up task.

Behavior-changing work is incomplete unless relevant automated tests are added or updated in the same change, except for strictly non-behavioral edits.

User-visible workflow changes are not complete until `bash app/scripts/test-system.sh` succeeds or the agent explicitly reports that full verification could not be completed.

### Backend

- run targeted `pytest` files in `app/tests/`
- add or update API tests for route, schema, or DB behavior changes
- use `app/scripts/test-system.sh` as the **canonical real-system completion command** — it builds the environment from scratch (bootstrap → db_setup/reset → startup lifecycle → backend suite → critical browser check) and stops on first failure; this is the single command that proves the product can boot from zero and its critical functionality works
- use `app/scripts/test-real-failfast.sh` (which delegates to `test-system.sh`) as the AI agent first-pass command before broader gates
- use `app/scripts/test-precommit.sh` as the local iteration gate before commits — it invokes `app/scripts/test-real-failfast.sh` first (which calls `test-system.sh` for environment-first setup), then adds an optional coverage report and UI checks
- use `app/scripts/test-full.sh` as a secondary broader gate for smoke coverage, Playwright route coverage validation, and optional extra UI coverage — it is downstream of `test-system.sh` and does not replace it as the primary real-system proof
- keep `/health` and every `/api/v1/**` route represented in `app/tests/test_api_smoke_matrix.py`, with scenarios sourced from `app/tests/api_smoke_registry/`
- keep connector/settings boundary assertions explicit: connector CRUD/auth-policy behavior belongs to `/api/v1/connectors*`, while `/api/v1/settings` covers app settings sections only
- keep builder catalog tests aligned to persisted `connector_endpoint_definitions` sourcing for `/api/v1/connectors/activity-catalog` and `/api/v1/connectors/http-presets`

### Primary Real-System Completion Command

`app/scripts/test-system.sh` is the **canonical single command** for real-system verification. It builds the environment from scratch and proves the product can boot from zero and its critical functionality works.

- **What it does**: provisions or attaches to the test database runtime → resets/creates the test database to a clean state each run → migrates the schema → runs `test_startup_lifecycle.py` → runs the full non-smoke pytest suite → runs the minimal critical Playwright browser subset → optionally runs the full Playwright browser suite.
- **When to use**: whenever you need to prove the product works end to end. This is the canonical completion gate for user-visible workflow changes, shared test infrastructure changes, and browser coverage validation.
- **Critical browser by default**: the minimal real Playwright subset (`--project=critical`) always runs unless `SKIP_BROWSER_SUITE=1` is set (e.g. environments where Playwright browsers are not installed).
- Set `INCLUDE_FULL_BROWSER_SUITE=1` to also run the full `test:e2e` suite as an additional step.
- On any failure, writes a JSON artifact to `app/tests/test-artifacts/system-result.json` with the following contract:

| Field | Description |
|---|---|
| `step` | Failure stage: `bootstrap`, `db_setup`, `startup_lifecycle`, `backend_suite`, `critical_browser`, `browser_suite`, or `all` (success) |
| `exit_code` | Non-zero on failure; `0` on success |
| `command` | The exact command string that failed, or `"test-system.sh"` on success |
| `first_error_lines` | JSON array of up to 40 lines from the end of the failed command's output |

### Fail-Fast Real-Test Runner

`app/scripts/test-real-failfast.sh` is the recommended first-pass command for AI agents and automated checks that need minimal token output.

- Delegates to `test-system.sh`, which builds the environment from scratch (bootstrap → db_setup/reset → startup_lifecycle → backend_suite → critical_browser) and stops on the first failure.
- On failure, `test-system.sh` writes `app/tests/test-artifacts/system-result.json`; `test-real-failfast.sh` also copies it to `app/tests/test-artifacts/failfast-result.json` for backward compatibility with any tooling that reads the legacy path.
- `app/scripts/test-external-probes.py` is informational-only (no assertions, always exits 0) and must not appear in any automated fail gate.
- `test-precommit.sh` invokes `test-real-failfast.sh` as its first step before adding coverage and UI gates. `test-full.sh` is a secondary broader gate (smoke coverage, Playwright route coverage) that sits downstream of `test-system.sh` and does not replace it as the primary real-system proof.

### Frontend

- run `npm run build` in `app/ui/` for page wiring, Vite input, or asset changes
- run `npm run test` in `app/ui/` for React test coverage when React code changes
- add or update `app/ui/e2e/` coverage whenever a user-visible workflow changes unless the change is strictly non-behavioral
- run `npm run test:e2e` in `app/ui/` for browser workflow coverage when validating the full gate
- ensure Playwright assertions cover the changed workflow behavior, not only route load or static render
- manually verify the served page route if HTML/script wiring changed

### Startup And Port Conflict Triage

When startup, test server launch, or Playwright execution fails, confirm what is already running before declaring a blocker unresolved.

Startup lifecycle coverage must include an explicit automated contract test in `tests/test_startup_lifecycle.py` that launches a real uvicorn startup process and captures stdout/stderr output to `data/logs/` when startup fails.

Required triage steps:

1. check active listeners/processes on expected ports (for example app, Vite, or Playwright web server ports)
2. inspect `data/logs/` for startup/runtime failures that accompany listener conflicts or partial startup
3. report the specific conflicting process or listener in the task output
4. remediate the conflict and rerun the same failing command to confirm recovery

Do not stop at a generic startup timeout message when listener/process diagnostics are available.

### Test Retirement

When removing or rewriting tests:

1. confirm the original behavior or contract was actually removed or replaced
2. remove the stale test in the same change that removes the covered behavior
3. add or update replacement coverage when the behavior still exists in a new shape
4. update `tests/test_api_smoke_matrix.py` and the `tests/api_smoke_registry/` package when an internal API route is added, removed, or renamed

Do not delete tests only because they are inconvenient or currently failing. Fix stale assertions, missing fixtures, or changed contracts explicitly.

### Verification Minimum

For code changes, agent responses must tell the user:

- what should happen
- what to click or inspect to confirm the result

---

## Practical Do And Do Not Rules (Testing Relevant)

> Cross-reference: root policy R-TEST-001 through R-TEST-008; [Rules Matrix](../AGENTS.md#rules-matrix).

Do:

- place tests beside the backend feature area they cover or under the React feature they cover (→ R-TEST-008)
- add or update relevant automated tests in the same change when behavior changes (→ R-TEST-008)

Do not:

- remove tests as a convenience workaround for failures (→ R-TEST-004)
- ship behavior changes without relevant automated test updates (→ R-TEST-008)
