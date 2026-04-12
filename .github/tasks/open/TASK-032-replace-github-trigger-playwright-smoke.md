## Execution steps

1. [x] [ui]
Files: app/ui/e2e/github-trigger.spec.ts
Action: Replace the current smoke placeholder with a real workflow test that creates a GitHub-trigger automation through the builder UI (owner/repo/event/secret), saves it, and verifies persisted trigger data via live backend behavior (no first-party route interception; follow AGENTS.md R-TEST-009 and app/tests/AGENTS.md frontend rules).
Completion check: `app/ui/e2e/github-trigger.spec.ts` no longer contains the string `smoke` in the test title/comments and includes assertions for saved GitHub trigger fields.

2. [x] [test]
Files: app/ui/e2e/coverage-route-map.json
Action: Update Playwright route-coverage mapping so `/automations/builder.html` reflects the new GitHub trigger workflow contract and references the new concrete test name.
Completion check: `app/ui/e2e/coverage-route-map.json` includes the updated GitHub-trigger workflow contract and points to the renamed non-smoke spec case.

3. [!] [docs]
Files: README.md
Action: Remove or rewrite the unfinished-features bullet that currently says GitHub trigger browser coverage is still a smoke placeholder.
Blocker: README.md was intentionally left untouched in this pass per the task ownership limit. The remaining doc delta is to remove the unfinished-features note that says `app/ui/e2e/github-trigger.spec.ts` is still a smoke placeholder.
Completion check: README no longer describes `app/ui/e2e/github-trigger.spec.ts` as a smoke placeholder.

## Test impact review

1. [ ] [test]
Files: app/ui/e2e/github-trigger.spec.ts
Action: Intent: provide real browser workflow proof for GitHub trigger creation and persistence; Recommended action: update; Validation command: `npm --prefix app/ui run test:e2e -- github-trigger.spec.ts`.
Completion check: Spec asserts the workflow outcome, not only route load/title visibility.

2. [ ] [test]
Files: app/ui/src/automation/__tests__/trigger-settings-form.github.test.tsx, app/ui/src/automation/__tests__/trigger-github-form.test.tsx
Action: Intent: preserve component-level trigger form coverage while e2e becomes end-to-end; Recommended action: keep.
Completion check: No edits are required unless form behavior changes during implementation.

3. [ ] [test]
Files: app/ui/e2e/coverage-route-map.json
Action: Intent: keep route-coverage registry aligned with changed workflow assertions; Recommended action: update; Validation command: `node app/scripts/check-playwright-route-coverage.mjs`.
Completion check: Coverage map references the new concrete GitHub trigger workflow test case.

## Testing

1. [!] [test]
Files: app/ui/e2e/github-trigger.spec.ts
Action: Run `npm --prefix app/ui run test:e2e -- github-trigger.spec.ts`.
Blocker: The Playwright run hit backend database connection errors while loading the live automation builder flow, so the browser test could not complete cleanly.
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/ui/e2e/coverage-route-map.json, app/scripts/check-playwright-route-coverage.mjs
Action: Run `node app/scripts/check-playwright-route-coverage.mjs`.
Completion check: Command exits with status 0 and reports no missing mapped workflows.

3. [!] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the first-pass real-system gate before broader validation.
Blocker: `backend_suite` failed during the real-system gate with `psycopg.errors.AdminShutdown` in `app/backend/services/automation_execution.py` while syncing the tools manifest.
Completion check: Command exits with status 0.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-032-replace-github-trigger-playwright-smoke.md, app/ui/e2e/github-trigger.spec.ts, app/ui/e2e/coverage-route-map.json, README.md
Action: Stage only relevant files and run `git add <files> && git commit -m "Replace GitHub trigger Playwright smoke with workflow test" && git push` per AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the listed files.
