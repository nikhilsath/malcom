## Execution steps

1. [ ] [test]
Files: ui/page-registry.json, ui/e2e/coverage-route-map.json
Action: Create a machine-readable Playwright coverage map that lists every served UI route from ui/page-registry.json and assigns at least one owning e2e spec plus a workflow contract summary for each route. Exclude redirect-only routes from the required-coverage set and document redirect assertions separately.
Completion check: ui/e2e/coverage-route-map.json exists, includes every served route path from ui/page-registry.json exactly once, and has no entries for redirect-only route paths.

2. [ ] [scripts]
Files: scripts/check-playwright-route-coverage.mjs, ui/e2e/coverage-route-map.json, ui/page-registry.json
Action: Add a deterministic Node validation script that fails when any served route lacks a mapped e2e owner, when a mapped spec file is missing, or when the map references unknown routes. Keep output actionable by printing missing/invalid route-spec links before exiting non-zero.
Completion check: Running node scripts/check-playwright-route-coverage.mjs validates the map against ui/page-registry.json and exits non-zero when the map is intentionally corrupted.

3. [ ] [scripts]
Files: scripts/test-precommit.sh, scripts/test-full.sh, ui/package.json
Action: Wire the new coverage validation into existing gates so route-to-spec mapping is checked before broad e2e execution. Keep command wiring consistent with existing repository test scripts and avoid introducing duplicate gate commands.
Completion check: scripts/test-precommit.sh and scripts/test-full.sh include the route-coverage validation command once each, and ui/package.json exposes a reusable script entry for the coverage check.

4. [ ] [ui]
Files: ui/e2e/settings.spec.ts, ui/e2e/support/dashboard-settings.ts
Action: Add replacement Playwright workflow coverage for /settings/access.html (save and reset behavior with visible feedback and stable control assertions) using existing settings fixtures so the served route is no longer uncovered.
Completion check: ui/e2e/settings.spec.ts contains a dedicated settings access workflow test that navigates to /settings/access.html and asserts save/reset outcomes, and support fixtures provide deterministic data needed by this test.

5. [ ] [test]
Files: ui/e2e/README.md, tests/impact/TASK-011-affected-tests.md
Action: Document the migration policy for retiring old Playwright tests: each retired test must map to replacement test IDs/specs in the coverage map, and deletions are blocked until replacement entries are present and passing. Record the concrete affected test inventory for this task in tests/impact/TASK-011-affected-tests.md.
Completion check: ui/e2e/README.md describes the replacement-first retirement rule, and tests/impact/TASK-011-affected-tests.md lists affected specs with replacement ownership.

## Test impact review

1. [ ] [test]
Files: ui/e2e/settings.spec.ts
Action: Intent: close uncovered served-route behavior for the access settings page with workflow assertions (not route-load only). Recommended action: update. Validation command: cd ui && npx playwright test e2e/settings.spec.ts
Completion check: The settings spec includes and passes a scenario covering /settings/access.html save/reset behavior and user feedback.

2. [ ] [test]
Files: ui/e2e/shell.spec.ts
Action: Intent: preserve canonical/legacy redirect behavior assertions while route coverage moves to a map-based gate. Recommended action: keep. Validation command: not required for keep.
Completion check: Existing legacy redirect assertions remain intact and still represent redirect-only routes.

3. [ ] [test]
Files: ui/e2e/*.spec.ts, ui/e2e/coverage-route-map.json
Action: Intent: ensure each served route has explicit ownership in the new coverage map during migration away from old Playwright suites. Recommended action: update. Validation command: node scripts/check-playwright-route-coverage.mjs
Completion check: Coverage map validation reports zero missing served routes and zero unknown route references.

4. [ ] [test]
Files: scripts/test-precommit.sh, scripts/test-full.sh
Action: Intent: prevent regressions where old tests are deleted without mapped replacements by enforcing coverage-map validation in standard gates. Recommended action: update. Validation command: ./scripts/test-precommit.sh
Completion check: Precommit gate runs the coverage-map check before broader browser execution and exits non-zero when coverage mapping is incomplete.

## Testing steps

1. [ ] [test]
Files: scripts/check-playwright-route-coverage.mjs, ui/e2e/coverage-route-map.json, ui/page-registry.json
Action: Run the route-to-spec coverage validator directly. Command: node scripts/check-playwright-route-coverage.mjs
Completion check: The command exits 0 with no missing served routes.

2. [ ] [test]
Files: ui/e2e/settings.spec.ts, ui/e2e/shell.spec.ts
Action: Run targeted Playwright regression for settings and redirect/navigation behavior. Command: cd ui && npx playwright test e2e/settings.spec.ts e2e/shell.spec.ts
Completion check: The command exits 0.

3. [ ] [test]
Files: scripts/test-precommit.sh
Action: Run the fast repository gate after targeted browser tests pass. Command: ./scripts/test-precommit.sh
Completion check: The command exits 0.

4. [ ] [test]
Files: scripts/test-full.sh
Action: Run the full repository completion gate, including full Playwright coverage. Command: ./scripts/test-full.sh
Completion check: The command exits 0.

## Documentation review

1. [ ] [docs]
Files: ui/e2e/README.md, README.md
Action: Update Playwright workflow documentation to reference the route-coverage map and validation script, and confirm README guidance for browser coverage remains consistent with the new migration gate.
Completion check: Documentation describes how to maintain full served-route coverage while replacing old tests and includes the validation command path.

## GitHub update

1. [ ] [github]
Files: .agents/tasks/open/TASK-011-playwright-coverage-migration-gate.md, ui/e2e/coverage-route-map.json, scripts/check-playwright-route-coverage.mjs, scripts/test-precommit.sh, scripts/test-full.sh, ui/package.json, ui/e2e/settings.spec.ts, ui/e2e/support/dashboard-settings.ts, ui/e2e/README.md, tests/impact/TASK-011-affected-tests.md, README.md
Action: Stage only task-relevant files, commit with a focused message such as Add Playwright served-route coverage gate and access-page workflow test, move this task file to .agents/tasks/closed/ in the same commit, then push.
Completion check: Commit includes only relevant implementation/test/doc files plus moving this task file to .agents/tasks/closed/, and push succeeds.
