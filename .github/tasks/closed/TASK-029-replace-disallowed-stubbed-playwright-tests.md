# TASK-029 replace disallowed stubbed Playwright tests

Assumption: `TASK-027-policy-first-real-test-runner-workflow.md` and `TASK-028-environment-first-real-system-test-workflow.md` have already been completed. This task removes the remaining disallowed stubbed Playwright coverage and replaces it with real end-to-end tests or lower-level non-Playwright tests where appropriate. The remaining single-command runner/bootstrap convergence work is tracked separately in `TASK-030-finish-single-command-real-system-test-runner.md`.

## Execution steps

1. [x] [test]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh, app/ui/playwright.config.ts
Action: Update policy and repo test documentation to explicitly forbid stubbed Playwright coverage. Remove any language that permits Playwright tests using `page.route()` or `installDashboardSettingsFixtures` for first-party backend flows. Remove the `stubbed` Playwright project and replace the current "secondary stubbed tier" wording with an explicit prohibition plus the replacement rule: browser tests must run against the real FastAPI app and real PostgreSQL test database, and isolated frontend-only state tests belong in Vitest rather than Playwright. Keep AGENTS.md and app/scripts/check-policy.sh synchronized per AGENTS.md#maintenance-sync-rule.
Completion check: `AGENTS.md`, `app/tests/AGENTS.md`, and `app/ui/e2e/README.md` explicitly forbid stubbed Playwright tests; `app/ui/playwright.config.ts` no longer defines a `stubbed` project; `app/scripts/check-policy.sh` contains enforcement for the no-stubbed-Playwright rule.

2. [x] [test]
Files: app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/support/dashboard-settings.ts, app/ui/src/dashboard/__tests__/dashboard-app.test.tsx
Action: Inspect the existing fully stubbed specs and replace each one with either: (a) a real Playwright test that hits the live backend/test DB, or (b) a lower-level Vitest/frontend test if the coverage target is purely UI logic and does not need browser/system proof. Remove any dependency on `installDashboardSettingsFixtures` and route interception for first-party endpoints. Delete `app/ui/e2e/support/dashboard-settings.ts` entirely if nothing valid remains in it after the conversion.
Completion check: `settings.spec.ts` and `shell.spec.ts` now run against the live backend/test DB without `installDashboardSettingsFixtures`; `dashboard.spec.ts` has been replaced by dashboard Vitest coverage in `app/ui/src/dashboard/__tests__/dashboard-app.test.tsx`; dead stub helper code is removed.

3. [x] [test]
Files: app/ui/e2e/automation-write-step.spec.ts, app/ui/e2e/connectors.spec.ts, app/ui/e2e/README.md, app/ui/src/automation/__tests__/automation-app.test.tsx
Action: Audit the partially stubbed Playwright specs and remove any remaining first-party route interception. Convert them into real Playwright flows where the workflow is product-critical, or move the isolated logic into Vitest if real browser coverage is unnecessary. Update the documentation so the real Playwright inventory is accurate after the conversion.
Completion check: `connectors.spec.ts` now exercises the live connectors API with no first-party route interception; `automation-write-step.spec.ts` has been replaced by focused Vitest coverage in `app/ui/src/automation/__tests__/automation-app.test.tsx`; `app/ui/e2e/README.md` accurately lists the remaining real Playwright specs only.

4. [x] [test]
Files: app/ui/package.json, app/ui/playwright.config.ts, app/scripts/test-system.sh, app/tests/AGENTS.md
Action: Re-evaluate the critical real Playwright subset after the stubbed specs are removed. Expand the `critical` project if necessary so `bash app/scripts/test-system.sh` proves more than a single browser workflow and covers the minimum real user-critical surfaces needed to support the claim that the product boots and core functionality exists. Keep this subset intentionally small and stable.
Completion check: `app/ui/playwright.config.ts` now points the `critical` project at the real `shell.spec.ts` + `settings.spec.ts` subset, and `npx playwright test --project=critical` passes from `app/ui`.

5. [x] [test]
Files: app/ui/src/dashboard/__tests__/dashboard-app.test.tsx, app/ui/src/automation/__tests__/automation-app.test.tsx, app/ui/package.json
Action: Where removed stubbed Playwright coverage was really testing pure frontend state/rendering logic, add or update Vitest coverage instead of re-creating fake browser/system tests. Keep the replacement tests narrowly focused and ensure they do not duplicate the real Playwright critical path.
Completion check: the dashboard collapse behavior and write-step UI/state cases now have Vitest coverage in the appropriate frontend test files, and `npm test` targeted at those files passes without needing stubbed Playwright.

## Test impact review

1. [x] [test]
Files: app/ui/e2e/settings.spec.ts
Action: replace — this spec is currently documented as fully stubbed and must be converted to a real backend/browser flow or split so the UI-only pieces move to Vitest.
Completion check: `cd app/ui && npx playwright test settings.spec.ts`

2. [x] [test]
Files: app/ui/e2e/dashboard.spec.ts, app/ui/src/dashboard/__tests__/dashboard-app.test.tsx
Action: replace — this spec was fully stubbed and has been replaced with Vitest coverage for the dashboard UI-only behavior.
Completion check: `cd app/ui && npm test -- src/dashboard/__tests__/dashboard-app.test.tsx`

3. [x] [test]
Files: app/ui/e2e/shell.spec.ts
Action: replace — this spec is currently documented as fully stubbed and must be converted to a real backend/browser flow or split so the UI-only pieces move to Vitest.
Completion check: `cd app/ui && npx playwright test shell.spec.ts`

4. [x] [test]
Files: app/ui/e2e/automation-write-step.spec.ts, app/ui/src/automation/__tests__/automation-app.test.tsx
Action: replace — remove partial stubbing for first-party routes and move the write-step UI/state coverage into Vitest because it is frontend logic rather than real browser/system proof.
Completion check: `cd app/ui && npm test -- src/automation/__tests__/automation-app.test.tsx`

5. [x] [test]
Files: app/ui/e2e/connectors.spec.ts
Action: update — remove partial stubbing for first-party routes and keep only real backend/browser coverage if the workflow remains product-critical.
Completion check: `cd app/ui && npx playwright test connectors.spec.ts`

6. [ ] [test]
Files: app/ui/playwright.config.ts, app/ui/e2e/README.md, AGENTS.md, app/tests/AGENTS.md, app/scripts/check-policy.sh
Action: update — the policy/docs/config layer must be revalidated after the no-stubbed-Playwright rule is implemented.
Completion check: `bash app/scripts/check-policy.sh`

## Testing

1. [ ] [test]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/ui/playwright.config.ts, app/scripts/check-policy.sh
Action: Run the policy enforcement checks after the stubbed-Playwright prohibition is implemented.
Completion check: `bash app/scripts/check-policy.sh`

2. [x] [test]
Files: app/ui/e2e/settings.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/connectors.spec.ts, app/ui/src/dashboard/__tests__/dashboard-app.test.tsx, app/ui/src/automation/__tests__/automation-app.test.tsx
Action: Run the converted browser specs directly, and run the Vitest replacements for the coverage moved out of Playwright, to verify they now pass without first-party backend stubbing.
Completion check: `cd app/ui && npx playwright test settings.spec.ts shell.spec.ts connectors.spec.ts --project=chromium && npm test -- src/dashboard/__tests__/dashboard-app.test.tsx src/automation/__tests__/automation-app.test.tsx`

3. [ ] [test]
Files: app/ui/package.json, app/ui/playwright.config.ts, app/scripts/test-system.sh
Action: Run the critical browser subset through the canonical real-system command and confirm the new critical surface is still small, stable, and real.
Completion check: `bash app/scripts/test-system.sh`

4. [ ] [test]
Files: app/scripts/test-precommit.sh, app/scripts/test-full.sh, app/ui/package.json
Action: Re-run the broader gates after the stubbed coverage removal to ensure the repo still validates successfully without the old stubbed project.
Completion check: `bash app/scripts/test-precommit.sh && bash app/scripts/test-full.sh`

5. [x] [test]
Files: app/ui/src/dashboard/__tests__/dashboard-app.test.tsx, app/ui/src/automation/__tests__/automation-app.test.tsx
Action: Run the frontend unit/component test suite after the Vitest replacements are added.
Completion check: `cd app/ui && npm test -- src/dashboard/__tests__/dashboard-app.test.tsx src/automation/__tests__/automation-app.test.tsx`

## GitHub update

1. [ ] [github]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh, app/ui/playwright.config.ts, app/ui/e2e/coverage-route-map.json, app/ui/e2e/settings.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/connectors.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/automation-write-step.spec.ts, app/ui/e2e/support/dashboard-settings.ts, app/ui/src/dashboard/__tests__/dashboard-app.test.tsx, app/ui/src/automation/__tests__/automation-app.test.tsx, .github/tasks/open/TASK-029-replace-disallowed-stubbed-playwright-tests.md
Action: When the work is complete, stage the relevant files only and update GitHub using the repo’s required workflow in AGENTS.md#github-update-workflow.
Completion check: `git add AGENTS.md app/tests/AGENTS.md app/ui/e2e/README.md app/scripts/check-policy.sh app/ui/playwright.config.ts app/ui/e2e/coverage-route-map.json app/ui/e2e/settings.spec.ts app/ui/e2e/shell.spec.ts app/ui/e2e/connectors.spec.ts app/ui/e2e/dashboard.spec.ts app/ui/e2e/automation-write-step.spec.ts app/ui/e2e/support/dashboard-settings.ts app/ui/src/dashboard/__tests__/dashboard-app.test.tsx app/ui/src/automation/__tests__/automation-app.test.tsx .github/tasks/open/TASK-029-replace-disallowed-stubbed-playwright-tests.md && git commit -m "Replace disallowed stubbed Playwright coverage" && git push`
