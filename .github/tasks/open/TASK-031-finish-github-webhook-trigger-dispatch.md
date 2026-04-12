## Execution steps

1. [x] [backend]
Files: app/backend/services/github_webhook.py, app/backend/services/apis.py
Action: Implement real GitHub-trigger dispatch instead of the current log-only placeholder by following AGENTS.md#implementation-quality-and-source-of-truth (R-FIX-001). Keep normalization in `github_webhook.py`, add matching against enabled `trigger_type = "github"` automations (`github_owner`, `github_repo`, `github_event_type`, optional branch/path filters), and execute through the canonical automation execution path.
Completion check: `app/backend/services/github_webhook.py` no longer contains the placeholder comment about future runtime queue integration, and `dispatch_normalized_event(` is called from `receive_webhook_event` in `app/backend/services/apis.py`.
Blocker: none.
Implemented in owned scope: `app/backend/services/github_webhook.py` now matches enabled GitHub automations and calls the canonical automation executor; `app/tests/test_github_webhooks.py` now covers matching and non-matching dispatch behavior.

2. [x] [test]
Files: app/tests/test_github_webhooks.py, app/tests/test_api_resources.py
Action: Expand tests from helper-only assertions to behavior coverage for GitHub trigger dispatch, including at least one matching and one non-matching automation case, plus webhook callback integration coverage that exercises the dispatch path.
Completion check: `app/tests/test_github_webhooks.py` asserts dispatch side effects (not only normalization), and `app/tests/test_api_resources.py` includes a GitHub webhook callback case that asserts automation trigger outcomes.

3. [x] [docs]
Files: README.md
Action: Update the unfinished-features list to remove the GitHub dispatch gap after implementation, following AGENTS.md#documentation-ownership-model (R-DOC-001).
Completion check: README no longer states that `app/backend/services/github_webhook.py` only logs dispatch intent.

## Test impact review

1. [x] [test]
Files: app/tests/test_github_webhooks.py
Action: Intent: verify GitHub event normalization plus trigger dispatch matching; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_github_webhooks.py`.
Completion check: Test file includes assertions for both matching and non-matching GitHub automation trigger filters.

2. [x] [test]
Files: app/tests/test_api_resources.py
Action: Intent: verify webhook callback integration executes GitHub-trigger automations through the API flow; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_resources.py -k github`.
Completion check: API resource coverage includes at least one GitHub callback path asserting triggered run behavior.

3. [x] [test]
Files: app/ui/e2e/github-trigger.spec.ts
Action: Intent: keep this file focused on browser builder workflow coverage handled by TASK-032; Recommended action: keep.
Completion check: No executor edits are required in this task file.

## Testing

1. [x] [test]
Files: app/tests/test_github_webhooks.py, app/tests/test_api_resources.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_github_webhooks.py app/tests/test_api_resources.py -k "github or webhook"`.
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the first-pass real-system gate per AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-031-finish-github-webhook-trigger-dispatch.md, app/backend/services/github_webhook.py, app/backend/services/apis.py, app/tests/test_github_webhooks.py, app/tests/test_api_resources.py, README.md
Action: After validation, stage only relevant files and run `git add <files> && git commit -m "Finish GitHub webhook trigger dispatch" && git push` following AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the files listed above.
