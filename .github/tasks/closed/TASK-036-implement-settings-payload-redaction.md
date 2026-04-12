## Execution steps

1. [x] [backend]
Files: app/backend/services/apis.py, app/backend/services/settings.py, app/backend/services/support.py
Action: Implement canonical payload-redaction behavior for stored inbound/webhook event samples based on `settings.data.payload_redaction` (mask token/secret/credential-like fields before persistence), rather than leaving redaction as a UI-only setting.
Completion check: Event persistence paths in `app/backend/services/apis.py` call a shared redaction utility gated by `settings.data.payload_redaction` before writing payload/header samples.
Blocker: none.

2. [x] [ui]
Files: app/ui/settings/data.html
Action: Remove the `(Coming soon)` redaction label and keep the existing toggle as the active behavior control.
Completion check: `app/ui/settings/data.html` no longer contains `(Coming soon)` in the payload-redaction description.

3. [x] [test]
Files: app/tests/test_api_resources.py, app/tests/test_settings_api.py, app/ui/e2e/settings.spec.ts
Action: Add/update tests to prove payload samples are redacted when enabled and preserved when disabled, plus browser coverage that confirms the settings toggle persists and affects backend behavior.
Completion check: Backend tests assert persisted event payload differences across redaction enabled/disabled states, and Playwright coverage asserts user-visible settings flow remains functional.
Blocker: none.

4. [x] [docs]
Files: README.md
Action: Remove the unfinished-features bullet stating payload redaction is coming soon once backend behavior and tests are complete.
Completion check: README no longer marks payload redaction as unfinished.
Blocker: none.

## Test impact review

1. [x] [test]
Files: app/tests/test_api_resources.py
Action: Intent: validate inbound/webhook event persistence applies redaction policy correctly; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_resources.py -k redaction`.
Completion check: API resource tests include assertions for redacted and non-redacted persisted payloads.

2. [x] [test]
Files: app/tests/test_settings_api.py
Action: Intent: verify `settings.data.payload_redaction` read/write behavior remains stable while gaining runtime effect; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_settings_api.py -k payload_redaction`.
Completion check: Settings API tests explicitly cover payload redaction toggle persistence.

3. [x] [test]
Files: app/ui/e2e/settings.spec.ts
Action: Intent: confirm browser workflow for Settings Data keeps working and reflects active redaction feature wording; Recommended action: update; Validation command: `npm --prefix app/ui run test:e2e -- settings.spec.ts`.
Completion check: Playwright settings workflow includes assertions for active redaction setting copy and persistence behavior.

## Testing

1. [x] [test]
Files: app/tests/test_api_resources.py, app/tests/test_settings_api.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_resources.py app/tests/test_settings_api.py -k "redaction or payload_redaction"`.
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/ui/e2e/settings.spec.ts
Action: Run `npm --prefix app/ui run test:e2e -- settings.spec.ts`.
Completion check: Command exits with status 0.

3. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as first-pass real-system verification.
Completion check: Command exits with status 0.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-036-implement-settings-payload-redaction.md, app/backend/services/apis.py, app/backend/services/settings.py, app/backend/services/support.py, app/ui/settings/data.html, app/tests/test_api_resources.py, app/tests/test_settings_api.py, app/ui/e2e/settings.spec.ts, README.md
Action: Stage only relevant files and run `git add <files> && git commit -m "Implement payload redaction for stored API event samples" && git push` per AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the listed files.
