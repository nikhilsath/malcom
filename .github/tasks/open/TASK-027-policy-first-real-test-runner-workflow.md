# TASK-027 policy-first real-test-runner workflow

## Execution steps

1. [ ] [test]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh
Action: Update the canonical testing policy first so AI agents are explicitly told to use `app/scripts/test-real-failfast.sh` as the first-pass command for minimal-context real-test verification, while keeping `app/scripts/test-precommit.sh` and `app/scripts/test-full.sh` as broader gates. In this same policy change, explicitly define stubbed Playwright coverage as secondary to real system verification for critical workflows. Follow AGENTS.md#maintenance-sync-rule, AGENTS.md#task-file-construction, and the testing policy references in AGENTS.md / app/tests/AGENTS.md. This task changes the policy that governs `.github/agents/task-builder.md` and `.github/agents/task-executor.md`, so execute this task directly rather than through those agents until the policy update is complete.
Completion check: `AGENTS.md`, `app/tests/AGENTS.md`, and `app/ui/e2e/README.md` all mention `app/scripts/test-real-failfast.sh`; `AGENTS.md` and `app/scripts/check-policy.sh` are both changed in the same diff; root policy text makes the first-pass AI command explicit.

2. [ ] [scripts]
Files: app/scripts/check-policy.sh
Action: Extend policy enforcement so testing-workflow policy changes are checked consistently. Add sync checks for the new real-test-runner policy language and any new rule IDs, Quick Task entries, or machine-index references introduced in `AGENTS.md`. Keep this aligned with AGENTS.md#maintenance-sync-rule (R-POLICY-001).
Completion check: `app/scripts/check-policy.sh` contains explicit checks for the real-test-runner policy language and fails when `AGENTS.md` is changed without the matching policy-enforcement update.

3. [ ] [test]
Files: app/scripts/test-real-failfast.sh, app/tests/AGENTS.md
Action: Tighten the fail-fast runner so every failure path, including PostgreSQL preflight failure, writes the same machine-readable artifact format to `app/tests/test-artifacts/failfast-result.json`. Keep the output shape small and stable for low-token AI debugging.
Completion check: `app/scripts/test-real-failfast.sh` writes `step`, `exit_code`, `command`, and `first_error_lines` for preflight failure, startup-lifecycle failure, backend-suite failure, and success; `app/tests/AGENTS.md` documents the final artifact contract.

4. [ ] [scripts]
Files: app/scripts/test-precommit.sh, app/scripts/test-full.sh, AGENTS.md, app/tests/AGENTS.md
Action: After the policy files are updated, realign the broader gates to the new policy. Decide whether they should invoke `app/scripts/test-real-failfast.sh` directly or remain separate but explicitly downstream of it. Keep the two-tier broader-gate model intact, but make the real-test runner the canonical first-pass path for AI agents. Update root and test policy text if the gate order or descriptions change.
Completion check: `app/scripts/test-precommit.sh` and/or `app/scripts/test-full.sh` reflect the post-policy design, and the final policy text matches the actual script behavior.

5. [ ] [test]
Files: app/ui/playwright.config.ts, app/ui/e2e/README.md, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/support/dashboard-settings.ts
Action: Audit the current real vs stubbed Playwright split and make the classification explicit and accurate. Preserve stubbed specs where they are still useful for isolated UI logic, but document that they are secondary and not the primary proof for critical workflows. If any of the listed specs are misclassified or partially stubbed in a way that the docs do not reflect, fix the docs and config in the same change.
Completion check: `app/ui/e2e/README.md` and `app/ui/playwright.config.ts` agree on which specs are real vs stubbed, and the documented classification matches the actual interception behavior in the named spec/support files.

## Test impact review

1. [ ] [test]
Files: app/tests/test_startup_lifecycle.py
Action: keep — this remains the highest-value real startup/backup contract and should continue to run first in the fail-fast path.
Completion check: none.

2. [ ] [test]
Files: app/ui/e2e/settings.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test settings.spec.ts --project=stubbed`

3. [ ] [test]
Files: app/ui/e2e/dashboard.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test dashboard.spec.ts --project=stubbed`

4. [ ] [test]
Files: app/ui/e2e/shell.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test shell.spec.ts --project=stubbed`

5. [ ] [test]
Files: app/scripts/test-real-failfast.sh
Action: update — this script is the main behavior change and must be revalidated after artifact/output adjustments.
Completion check: `bash app/scripts/test-real-failfast.sh`

6. [ ] [test]
Files: app/scripts/check-policy.sh
Action: update — policy enforcement must be revalidated after the new sync checks are added.
Completion check: `bash app/scripts/check-policy.sh`

## Testing

1. [ ] [test]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh
Action: Run the policy enforcement checks after the policy-first change to confirm the repo accepts the new canonical testing workflow.
Completion check: `bash app/scripts/check-policy.sh`

2. [ ] [test]
Files: app/scripts/test-real-failfast.sh, app/tests/test_startup_lifecycle.py, app/tests/test-artifacts/failfast-result.json
Action: Run the fail-fast real-test runner and verify both terminal output and the machine-readable artifact contract.
Completion check: `bash app/scripts/test-real-failfast.sh`

3. [ ] [test]
Files: app/ui/playwright.config.ts, app/ui/e2e/README.md, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts
Action: Validate the documented stubbed Playwright project and ensure the named stubbed specs still execute under that classification.
Completion check: `cd app/ui && npx playwright test --project=stubbed`

4. [ ] [test]
Files: app/scripts/test-precommit.sh, app/scripts/test-full.sh
Action: After any gate-script changes, rerun the broader gates to confirm the post-policy workflow remains operational.
Completion check: `bash app/scripts/test-precommit.sh && bash app/scripts/test-full.sh`

## GitHub update

1. [ ] [github]
Files: AGENTS.md, app/tests/AGENTS.md, app/ui/e2e/README.md, app/scripts/check-policy.sh, app/scripts/test-real-failfast.sh, app/scripts/test-precommit.sh, app/scripts/test-full.sh, app/ui/playwright.config.ts, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/support/dashboard-settings.ts, .github/tasks/open/TASK-027-policy-first-real-test-runner-workflow.md
Action: When the work is complete, stage the relevant files only and update GitHub using the repo’s required workflow in AGENTS.md#github-update-workflow.
Completion check: `git add AGENTS.md app/tests/AGENTS.md app/ui/e2e/README.md app/scripts/check-policy.sh app/scripts/test-real-failfast.sh app/scripts/test-precommit.sh app/scripts/test-full.sh app/ui/playwright.config.ts app/ui/e2e/settings.spec.ts app/ui/e2e/dashboard.spec.ts app/ui/e2e/shell.spec.ts app/ui/e2e/support/dashboard-settings.ts .github/tasks/open/TASK-027-policy-first-real-test-runner-workflow.md && git commit -m "Align policy and gates around real fail-fast tests" && git push`
