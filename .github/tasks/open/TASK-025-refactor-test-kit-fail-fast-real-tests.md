# TASK-025 — Refactor test kit: fail-fast real-test runner and real-vs-stubbed classification

## Context

Goal: Make the default AI-facing test command focus on real executable tests, stop on the first failure, and emit a minimal machine-readable failure summary.  The existing two-tier workflow (test-precommit.sh / test-full.sh) is kept but repositioned.

Verified repo state at task creation:

- Real startup/backup lifecycle tests live in `app/tests/test_startup_lifecycle.py` (3 test methods: `test_launcher_starts_real_uvicorn_and_serves_health`, `test_launcher_can_create_and_restore_real_backup_while_running`, `test_launcher_captures_startup_errors_when_boot_fails`).
- `app/scripts/test-precommit.sh` runs `require_test_database.py` → pytest startup lifecycle → full pytest suite (no smoke marker) → `check-ui-page-entry-modules.mjs` → optionally playwright route coverage → `npm test` → `npm run build`.
- `app/scripts/test-full.sh` runs `test:e2e:coverage` → `test-precommit.sh` (SKIP_PLAYWRIGHT_ROUTE_COVERAGE=1) → pytest smoke marker → `test-external-probes.py` → `npm run test:e2e`.
- `app/scripts/test-external-probes.py` is an informational connector-probe manifest printer (177 lines, no assertions, exit 0 always). It is currently the last step of `test-full.sh` and must be removed from the critical test path.
- `app/scripts/require_test_database.py` — PostgreSQL preflight.  `app/scripts/reset_playwright_test_db.py` — Playwright DB reset.
- Playwright specs with route stubs (i.e. `page.route(…)` or `installDashboardSettingsFixtures` calls):
  - `app/ui/e2e/settings.spec.ts` — 12 stub references, all tests use `installDashboardSettingsFixtures` (fully stubbed API layer, no real server calls)
  - `app/ui/e2e/dashboard.spec.ts` — 5 stub references, all tests use `installDashboardSettingsFixtures`
  - `app/ui/e2e/shell.spec.ts` — 4 stub references, all tests use `installDashboardSettingsFixtures`
  - `app/ui/e2e/automation-write-step.spec.ts` — 2 stub references via `page.route`
  - `app/ui/e2e/connectors.spec.ts` — 1 stub reference via `page.route`
- Playwright specs with zero stubs (fully real against live test server): `apis-incoming`, `apis-outgoing`, `apis-registry`, `apis-webhooks`, `automations-builder`, `automations-data`, `automations-library`, `automations-overview`, `github-trigger`, `scripts-library`, `tools-catalog`, `tools-coqui-tts`, `tools-image-magic`, `tools-llm-deepl`, `tools-smtp`.
- `app/ui/e2e/support/dashboard-settings.ts` (798 lines) — the shared stub harness for `installDashboardSettingsFixtures`.
- `app/ui/playwright.config.ts` — defines Playwright projects; web server launched via `app/scripts/run_playwright_server.sh`.
- `app/pytest.ini` — `testpaths = app/tests`, markers: `smoke`, `integration`.
- `app/tests/test-artifacts/` — existing test artifact output directory used by startup lifecycle tests.

---

## Execution steps

1. [ ] [scripts]
   Files: `app/scripts/test-real-failfast.sh`
   Action: Create a new executable shell script. It must:
   - Set `set -euo pipefail` and resolve `WORKSPACE_ROOT` the same way as `test-precommit.sh`.
   - Run `.venv/bin/python app/scripts/require_test_database.py` as the first step; exit non-zero with message `"PostgreSQL preflight failed"` if it fails.
   - Run `.venv/bin/pytest -c app/pytest.ini -x -q --tb=short app/tests/test_startup_lifecycle.py` as the second step (startup/backup lifecycle, highest-value real tests first).
   - On failure, capture the pytest exit code and the last 40 lines of its output, write a JSON artifact to `app/tests/test-artifacts/failfast-result.json` with fields: `{ "step": "startup_lifecycle", "exit_code": <int>, "command": "<string>", "first_error_lines": ["..."] }`, then exit 1.
   - Run `.venv/bin/pytest -c app/pytest.ini -x -q --tb=short -m "not smoke" app/tests/` as the third step (full real-test suite, fail on first failure).
   - On failure, capture the exit code and last 40 output lines, write `app/tests/test-artifacts/failfast-result.json` with fields: `{ "step": "backend_suite", "exit_code": <int>, "command": "<string>", "first_error_lines": ["..."] }`, then exit 1.
   - On full success, write `app/tests/test-artifacts/failfast-result.json` with `{ "step": "all", "exit_code": 0, "command": "test-real-failfast.sh", "first_error_lines": [] }` and print `"All real tests passed."` to stdout.
   - Do NOT call `test-external-probes.py`, `npm test`, `npm run build`, or any Playwright commands. The script is Python-only, real-test-only.
   Completion check: `app/scripts/test-real-failfast.sh` exists, is executable (`ls -l` shows `x` bit), contains `test_startup_lifecycle.py` and `failfast-result.json`, and does not contain `test-external-probes`.

2. [ ] [scripts]
   Files: `app/scripts/test-full.sh`
   Action: Remove the `test-external-probes.py` call from `test-full.sh`. The line `./.venv/bin/python app/scripts/test-external-probes.py` is currently the second-to-last step. Delete that line. Do not add any replacement — the probes file is informational and does not belong in any automated fail gate.
   Completion check: `grep -c "test-external-probes" app/scripts/test-full.sh` returns `0`.

3. [ ] [test]
   Files: `app/ui/playwright.config.ts`
   Action: Add a second Playwright project named `"stubbed"` alongside (or after) the existing default project. Configure the `"stubbed"` project to run only the stub-heavy specs by setting its `testMatch` (or `testDir` + `testMatch`) to include: `settings.spec.ts`, `dashboard.spec.ts`, `shell.spec.ts`. The existing default project should exclude those three files by adding a corresponding `testIgnore` (or negative `testMatch`) entry so they are not double-run. Do not change the default project's browser or device config. Keep the `webServer` config unchanged.
   Completion check: `app/ui/playwright.config.ts` contains `"stubbed"` as a project name and references `settings.spec.ts` in that project's match config.

4. [ ] [test]
   Files: `app/ui/e2e/README.md`
   Action: Add a section titled `## Test Classification` that defines the two tiers:
   - **Real** — specs that make no `page.route()` intercepts and run against the live Playwright test server (reset DB). List the real specs by filename.
   - **Stubbed** — specs that use `installDashboardSettingsFixtures` or `page.route()` to intercept API calls; these test UI logic and rendering under controlled state rather than end-to-end system behavior. List: `settings.spec.ts`, `dashboard.spec.ts`, `shell.spec.ts`, and partially `automation-write-step.spec.ts`, `connectors.spec.ts`.
   - Add a note that the `"stubbed"` Playwright project in `playwright.config.ts` targets stub-heavy specs.
   - Add a note that `test-real-failfast.sh` runs only backend real tests (no Playwright) and is the recommended first-pass check for AI agents.
   Completion check: `app/ui/e2e/README.md` contains the string `## Test Classification`.

5. [ ] [test]
   Files: `app/tests/AGENTS.md`
   Action: Add a subsection under `### Backend` (or after it as a peer section) titled `### Fail-Fast Real-Test Runner` that:
   - Names `app/scripts/test-real-failfast.sh` as the recommended first-pass command for AI agents and automated checks that need minimal token output.
   - States that it runs `test_startup_lifecycle.py` first, then the full non-smoke pytest suite with `-x`.
   - States that it writes a JSON artifact to `app/tests/test-artifacts/failfast-result.json` on failure.
   - States that `test-external-probes.py` is informational-only and must not appear in any automated fail gate.
   - States that the two-tier gates (`test-precommit.sh` / `test-full.sh`) remain the broader completion gates per R-TEST-002.
   Completion check: `app/tests/AGENTS.md` contains `test-real-failfast.sh` and `failfast-result.json`.

---

## Test impact review

| File | Intent | Action | Validation command |
|------|--------|--------|--------------------|
| `app/tests/test_startup_lifecycle.py` | Boots real Uvicorn, checks /health, exercises backup/restore, verifies startup error capture | **keep** — this is the anchor test that runs first in the new fail-fast script | n/a |
| `app/ui/e2e/settings.spec.ts` | UI settings save/reset flows using fully stubbed API responses | **keep** — reclassified as `stubbed` project in playwright.config.ts; no test lines removed | `cd app/ui && npx playwright test --project=stubbed e2e/settings.spec.ts` |
| `app/ui/e2e/dashboard.spec.ts` | Dashboard rendering under stubbed log/settings API | **keep** — reclassified as `stubbed` project; no test lines removed | `cd app/ui && npx playwright test --project=stubbed e2e/dashboard.spec.ts` |
| `app/ui/e2e/shell.spec.ts` | Shell nav active states under stubbed settings API | **keep** — reclassified as `stubbed` project; no test lines removed | `cd app/ui && npx playwright test --project=stubbed e2e/shell.spec.ts` |
| All other `app/ui/e2e/*.spec.ts` | Real end-to-end flows against live test server | **keep** — remain in default Playwright project unchanged | n/a |
| `app/scripts/test-external-probes.py` | Informational connector probe manifest (no assertions) | **keep file** but remove from `test-full.sh` call chain — not a test, should not be in a fail gate | n/a |

No existing test is removed. No stale assertion is introduced. The only behavioral change to existing scripts is the removal of `test-external-probes.py` from `test-full.sh`.

---

## Testing

1. [ ] [test]
   Files: none (validation only)
   Action: After step 1, from `WORKSPACE_ROOT`, run: `./.venv/bin/python app/scripts/require_test_database.py && bash app/scripts/test-real-failfast.sh` and confirm it exits 0, prints `"All real tests passed."`, and writes `app/tests/test-artifacts/failfast-result.json` with `"exit_code": 0`.
   Completion check: `cat app/tests/test-artifacts/failfast-result.json | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['exit_code']==0"` passes.

2. [ ] [test]
   Files: none (validation only)
   Action: After step 2, confirm `test-full.sh` no longer references `test-external-probes`:
   `grep "test-external-probes" app/scripts/test-full.sh && echo FAIL || echo PASS`
   Expected: prints `PASS`.
   Completion check: the grep exits non-zero (no match).

3. [ ] [test]
   Files: none (validation only)
   Action: After step 3, confirm both Playwright projects are recognized:
   `cd app/ui && npx playwright test --list --project=stubbed 2>&1 | head -20`
   Expected: lists tests from `settings.spec.ts`, `dashboard.spec.ts`, or `shell.spec.ts` under the `stubbed` project.
   Completion check: output contains at least one test name from those three spec files.

4. [ ] [test]
   Files: none (validation only)
   Action: Run `app/scripts/test-precommit.sh` to confirm the existing two-tier gate still passes with the changes made in steps 1–5. This validates that the new script and Playwright config changes do not break the broader gate.
   Completion check: `test-precommit.sh` exits 0.

---

## GitHub update

1. [ ] [github]
   Files: `app/scripts/test-real-failfast.sh`, `app/scripts/test-full.sh`, `app/ui/playwright.config.ts`, `app/ui/e2e/README.md`, `app/tests/AGENTS.md`
   Action: Follow AGENTS.md#github-update-workflow — stage the five files above, commit with message `"test: add fail-fast real-test runner, classify stubbed Playwright specs, drop informational probes from full gate"`, and push.
   Completion check: `git log --oneline -1` shows the commit message above.
