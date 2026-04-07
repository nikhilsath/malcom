# tests/AGENTS.md

Root policy remains authoritative in AGENTS.md.
This file defines testing and verification rules and should be read after root routing.

## Scope

Applies to backend tests, frontend tests, Playwright workflow coverage, smoke matrix obligations, and startup triage for test execution blockers.

---

## Testing And Verification

> Rule IDs from root policy: R-TEST-001 through R-TEST-008. See [Rules Matrix](../AGENTS.md#rules-matrix) for full definitions.

Every meaningful code change should include the smallest relevant verification set.

Build tests as implementation progresses rather than deferring all coverage to a follow-up task.

Behavior-changing work is incomplete unless relevant automated tests are added or updated in the same change, except for strictly non-behavioral edits.

User-visible workflow changes are not complete until `./scripts/test-full.sh` succeeds or the agent explicitly reports that full verification could not be completed.

### Backend

- run targeted `pytest` files in `tests/`
- add or update API tests for route, schema, or DB behavior changes
- use `scripts/test-precommit.sh` as the fast local backend/frontend iteration gate before commits
- use `scripts/test-full.sh` as the completion gate when backend route smoke coverage, browser coverage, or shared test infrastructure changes are involved
- keep `/health` and every `/api/v1/**` route represented in `tests/test_api_smoke_matrix.py`, with scenarios sourced from `tests/api_smoke_registry/`
- keep connector/settings boundary assertions explicit: connector CRUD/auth-policy behavior belongs to `/api/v1/connectors*`, while `/api/v1/settings` covers app settings sections only
- keep builder catalog tests aligned to persisted `connector_endpoint_definitions` sourcing for `/api/v1/connectors/activity-catalog` and `/api/v1/connectors/http-presets`

### Frontend

- run `npm run build` in `ui/` for page wiring, Vite input, or asset changes
- run `npm run test` in `ui/` for React test coverage when React code changes
- add or update `ui/e2e/` coverage whenever a user-visible workflow changes unless the change is strictly non-behavioral
- run `npm run test:e2e` in `ui/` for browser workflow coverage when validating the full gate
- ensure Playwright assertions cover the changed workflow behavior, not only route load or static render
- manually verify the served page route if HTML/script wiring changed

### Startup And Port Conflict Triage

When startup, test server launch, or Playwright execution fails, confirm what is already running before declaring a blocker unresolved.

Startup lifecycle coverage must include an explicit automated contract test in `tests/test_startup_lifecycle.py` that exercises FastAPI lifespan boot/shutdown behavior.

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
