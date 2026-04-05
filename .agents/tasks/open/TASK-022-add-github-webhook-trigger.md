Execution steps

1. [ ] [Route: backend]
Files: backend/database.py, backend/services/, backend/routes/, backend/services/workflow_builder.py, backend/routes/automations.py, backend/routes/connectors.py, backend/tool_registry.py, migrations/, tests/
Action: Discovery pass — verify the repository's current source-of-truth for automation triggers, connectors, inbound APIs, and any existing webhook/inbound delivery handling. Inspect these files/locations to determine whether a generic inbound-trigger system already exists and where trigger bindings are stored (DB table, settings, connectors table, or code-only). Produce a short discovery note at .agents/tasks/open/TASK-022-discovery.md that records: (a) the canonical trigger storage (table/file), (b) where automation trigger types are registered, (c) existing inbound/post-receive routes, (d) recommended anchor points for a new GitHub-specific inbound route and service.
Completion check: `.agents/tasks/open/TASK-022-discovery.md` exists and contains concrete statements naming the exact file(s) and table(s) (or "none") that currently hold trigger bindings, and a decision: "reuse X" or "create dedicated github_webhooks path".
Note: Per TASK-019 modularization rules, if discovery determines a new service/module is required, include creation of a module contract file under `.agents/module-contracts/github_webhook.md` as part of the same PR that implements the service. The discovery note must explicitly state the module contract filename and owner if new modules are proposed.

2. [ ] [Route: backend]
Files: backend/routes/webhooks_github.py, backend/routes/__init__.py
Action: Add a dedicated inbound route module `backend/routes/webhooks_github.py` that exposes a POST endpoint (suggested path `/api/v1/webhooks/github`) to receive GitHub deliveries. Register/import the module where routes are aggregated (e.g., `backend/routes/__init__.py` or whichever route registration file the discovery step identified). The handler should parse request headers/body and call a verify-and-dispatch service (to be implemented later). Do not implement business logic here beyond basic request parsing and delegation.
Completion check: `backend/routes/webhooks_github.py` exists with a POST handler function and the route module is imported/registered in the repository's route aggregation file identified in discovery.

3. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/__init__.py
Action: Add a small service module `backend/services/github_webhook.py` with functions:
- `verify_signature(headers, body, secret)` — implements GitHub HMAC hex digest verification (sha256) using a secret.
- `extract_delivery_id(headers)` — returns the `X-GitHub-Delivery` header value.
- `dispatch_normalized_event(normalized_event)` — placeholder that delegates to Malcom's automation trigger API/service discovered earlier.
Wire the route handler to call `verify_signature` and `extract_delivery_id` before dispatch.
Completion check: `backend/services/github_webhook.py` exists with the three functions implemented and `backend/routes/webhooks_github.py` imports and calls them.

Additional completion check: A module contract `.agents/module-contracts/github_webhook.md` has been created describing the service owner, public API, dependencies, and test obligations. Include unit + contract tests in the same PR and verify via `scripts/test-module.sh github_webhook` or the nearest relevant module name.

4. [ ] [Route: backend/db]
Files: backend/database.py, migrations/versions/, migrations/env.py (if present)
Action: Add durable storage for GitHub webhook bindings and delivery dedupe/audit. Propose and create:
- a new table `github_webhook_bindings` (or a documented alternative if reuse is decided) with fields: `id`, `owner`, `repo`, `event_type`, `branch_filter`, `path_filter`, `secret_value_or_secret_id`, `enabled`, `created_at`, `updated_at`.
- a new audit/dedupe table `github_webhook_deliveries` with fields: `id`, `delivery_id` (unique), `received_at`, `status`, `payload_summary`, `binding_id` (nullable FK).
Add migration skeleton in `migrations/versions/` to create these tables (executor will generate exact migration code).
Completion check: `backend/database.py` has the model/table definitions added or a clear comment added indicating where to persist the new tables, and a new migration file exists under `migrations/versions/` that creates the two tables (file present, not necessarily executed).

Note: Ensure the migration and any new table ownership are reflected in a module contract (either `github_webhook` or the canonical DB module) so table ownership follows R-SOT-001 and TASK-019 rules.

5. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/automation_normalizers.py (or file discovered)
Action: Implement payload normalization: add `normalize_github_event(payload, event_type)` producing Malcom's internal automation/event model (fields: source, repo, owner, event_type, ref/branch, affected_paths, actor, timestamp, raw_payload). The normalizer must convert core GitHub events (push, pull_request opened/closed/synchronized, etc.) into a consistent internal shape and return both the normalized event and metadata for matching configured bindings.
Completion check: `normalize_github_event` is present and referenced by the route/service; the discovery note lists which internal automation API function it will call to dispatch normalized events.

6. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/database.py
Action: Implement idempotency/dedupe by storing `X-GitHub-Delivery` values in `github_webhook_deliveries` and rejecting duplicate deliveries (or otherwise marking duplicates as deduped). The service must log and persist status for each delivery (accepted, rejected-signature, duplicate, dispatch-failed, dispatched).
Completion check: `github_webhook_deliveries` table (or equivalent) is created by migration and `github_webhook.py` calls insertion + uniqueness check on delivery processing.

7. [ ] [Route: backend]
Files: backend/services/workflow_builder.py, backend/routes/automations.py, backend/services/automation_registry.py (or discovered equivalents)
Action: Add backend support for a `github` trigger type in the workflow-builder/automation trigger registration: expand the trigger registry/resolver so the builder API exposes `github` triggers and supports binding fields: `owner`, `repo`, `event_type`, `branch_filter`, `path_filter`, `secret` (or reference to stored secret). Ensure that runtime trigger matching uses normalized events and the bindings table added earlier.
Completion check: the backend trigger registry contains an entry for `github` and the API that lists available trigger types returns `github` with the expected input schema.

8. [ ] [Route: ui]
Files: ui/src/automation/ (files implementing trigger configuration UI), ui/src/automation/app.tsx (or equivalent builder entry), ui/src/automation/step-editors/ (if present)
Action: Add a UI form/component for creating/editing a `github` trigger in the workflow builder. The form must collect `owner`, `repo`, `event_type` (select list), optional `branch/ref` filter, optional `path` filter, and secret input (or selection if secrets are stored). Hook the UI to the backend builder API created/expanded in step 7.
Completion check: New component file(s) exist in `ui/src/automation/` and the builder UI exposes a `GitHub` trigger option that posts the expected payload to the backend API path discovered earlier.

9. [ ] [Route: backend/test]
Files: tests/test_github_webhooks.py, tests/test_workflow_builder_service.py, tests/test_automations_api.py
Action: Add unit tests:
- signature verification: valid signature accepted; invalid signature rejected (negative).
- dedupe: same delivery id posted twice results in duplicate handling.
- normalization: sample GitHub push payload normalized into expected internal event shape.
- trigger dispatch: end-to-end unit test where a normalized event causes the workflow trigger path to be invoked (can mock downstream executor).
Create test files under `tests/` and wire any fixtures as needed.
Completion check: `tests/test_github_webhooks.py` exists with tests for signature, dedupe, normalization, and dispatch placeholders.

Additional completion check: Tests and module contract are added in the same PR and the module-scoped tests run under `scripts/test-module.sh github_webhook` (or the appropriate module name) as part of the PR validation.

10. [ ] [Route: ui/test]
Files: ui/e2e/, ui/e2e/github-trigger.spec.ts (or .js)
Action: Add Playwright test(s) that exercise the UI flow for creating a GitHub trigger in the builder and a mocked backend response verifying the binding was persisted. If the repository's UI e2e harness requires fixtures or metadata, add the minimal test under `ui/e2e/` consistent with existing conventions.
Completion check: new test file(s) exist under `ui/e2e/` and reference the UI pages/components added in step 8.

11. [ ] [Route: backend/docs]
Files: docs/github-webhooks.md, README.md
Action: Add documentation describing how to configure GitHub webhooks for Malcom: recommended webhook URL, which events to subscribe to, how to set the secret, an example push payload mapping to Malcom's fields, and instructions for using the workflow builder to create bindings. Include guidance on idempotency and delivery dedupe behavior.
Completion check: `docs/github-webhooks.md` exists and references the backend endpoint path and builder UI location.

12. [ ] [Route: backend]
Files: backend/routes/webhooks_github.py, backend/services/github_webhook.py, backend/services/workflow_builder.py, backend/database.py
Action: Add logging and auditability: ensure each delivery is logged with delivery id, signature check result, binding match result, and dispatch outcome. Persist an audit row per delivery in `github_webhook_deliveries` as implemented in step 4. Ensure logs are structured (logger name, level, delivery_id).
Completion check: new logging statements exist in `backend/services/github_webhook.py` and audit insert occurs for every processed delivery.

13. [ ] [Route: backend]
Files: tests/test_github_webhooks.py, tests/test_workflow_builder_service.py, ui/e2e/github-trigger.spec.ts
Action: Update existing affected tests discovered in step 1. For each affected test file identified in Test Impact Review, apply the recommended action (keep, update, replace, remove) and implement minimal test changes so that the new `github` trigger is covered and existing behavior is preserved.
Completion check: test files identified in Test Impact Review have been modified/added per the recommended actions (files present with updates).

14. [ ] [Route: backend]
Files: .agents/tasks/open/TASK-022-discovery.md
Action: If step 1 (discovery) resulted in choosing to reuse an existing inbound-trigger system instead of adding dedicated routes/tables, update all downstream steps (2–13) to point to the reuse locations and adjust file targets accordingly. This is a required conditional reconciliation step before coding begins.
Completion check: `.agents/tasks/open/TASK-022-discovery.md` updated with the "reuse" decision and all downstream step file lists adjusted to reference the actual reuse locations.

15. [ ] [Route: github]
Files: (list of files changed by implementation — to be filled by executor before commit)
Action: GitHub commit: stage only the files changed for this task and commit with a concise message like "Add GitHub webhook inbound endpoint, storage, normalization, and builder support" and push. Also move this task file from `.agents/tasks/open/TASK-022-add-github-webhook-trigger.md` to `.agents/tasks/closed/TASK-022-add-github-webhook-trigger.md` in the same commit per repo policy.
Completion check: A single commit exists on the branch that adds/updates only the task-relevant files and moves the task file to `.agents/tasks/closed/`.

Test impact review

1. tests/test_workflow_builder_service.py
- Intent: verifies trigger registration and builder-side behaviors.
- Recommended action: update — add expectations for `github` trigger type and adjust fixtures if trigger registry signatures changed.
- Validation command: `pytest tests/test_workflow_builder_service.py::test_github_trigger_registration` (new/updated test name).

2. tests/test_automations_api.py
- Intent: route-level automation/trigger APIs.
- Recommended action: update — add tests asserting inbound dispatch of normalized events works and that the automation API accepts normalized payloads from the webhook flow.
- Validation command: `pytest tests/test_automations_api.py::test_github_webhook_dispatch`.

3. tests/test_connectors_api.py and tests/test_connectors_for_builder*.py
- Intent: connector availability and builder connector flows.
- Recommended action: keep or update depending on discovery: if GitHub connector already exists and can manage secrets, update to assert secret linkage; otherwise keep unchanged.
- Validation command (if updated): `pytest tests/test_connectors_for_builder.py::test_github_secret_binding`.

4. tests/test_ui_html_routes.py and any UI unit tests under ui/src/automation/__tests__/
- Intent: ensure builder UI pages load and expose triggers.
- Recommended action: update — add unit tests for the new GitHub trigger form and update route coverage asserts if page entries changed.
- Validation command: `npm test` or repository-specific UI test command for the updated files.

5. ui/e2e/
- Intent: Playwright coverage validating the end-to-end trigger creation UX.
- Recommended action: add new Playwright test(s) that create a GitHub trigger in the builder and assert API persistence.
- Validation command: `npm run test:e2e` (or the project's e2e runner).

6. New tests to add
- `tests/test_github_webhooks.py` — create (signature, dedupe, normalization, dispatch).
- `ui/e2e/github-trigger.spec.ts` — create (UI create/edit flow).

Testing steps

1. [ ] [Route: test]
Files: tests/test_github_webhooks.py
Action: Run targeted unit tests for signature verification and normalization locally and iterate until passing. Use the workspace test fixtures and a local test secret for signature verification tests.
Completion check: `pytest tests/test_github_webhooks.py` exits 0 locally (or tests pass in CI-equivalent environment).

2. [ ] [Route: test]
Files: tests/test_workflow_builder_service.py, tests/test_automations_api.py
Action: Run and update the backend service-level tests that cover trigger registration and dispatch. Fix mock wiring as needed so the `github` trigger path is exercised.
Completion check: `pytest tests/test_workflow_builder_service.py::... tests/test_automations_api.py::...` pass locally.

3. [ ] [Route: ui/test]
Files: ui/e2e/github-trigger.spec.ts
Action: Run Playwright e2e test(s) added for the builder UI flow. If Playwright environment needs setup, follow project conventions (headless/local runner).
Completion check: Playwright test file runs and passes locally against the dev server.

4. [ ] [Route: test]
Files: (all changed test files)
Action: Run `scripts/test-precommit.sh` (or the repo's precommit test script) to validate changed unit tests integrate with the established CI checks.
Completion check: `scripts/test-precommit.sh` returns success.

Documentation review

1. [ ] [Route: docs]
Files: docs/github-webhooks.md, README.md
Action: Add usage and setup documentation described in Execution step 11 and cross-link to workflow-builder UI docs and connector secrets docs (if present). Verify examples include the exact inbound route path and recommended GitHub event subscription list.
Completion check: `docs/github-webhooks.md` exists and references the new route and builder UI location.

2. [ ] [Route: docs]
Files: backend/AGENTS.md, AGENTS.md
Action: If repository policy requires, update `AGENTS.md` or `backend/AGENTS.md` to mention the new `github` trigger type and any policy entries (e.g., audit/dedupe behavior).
Completion check: the relevant AGENTS.md file contains a short note referencing GitHub webhook trigger support.

GitHub update

1. [ ] [Route: github]
Files: (executor will fill in the list of modified/created files)
Action: Commit only the task-relevant files (routes, services, migrations, tests, UI components, docs) with a focused commit message: "Add GitHub webhook inbound endpoint, durable bindings, normalization, and builder UI support". Move `.agents/tasks/open/TASK-022-add-github-webhook-trigger.md` to `.agents/tasks/closed/TASK-022-add-github-webhook-trigger.md` in the same commit and push to the current branch.
Completion check: `git log -1` shows the focused commit and the task file is present under `.agents/tasks/closed/` in that commit.

Notes / executor guidance
- Strictly verify discovery step outcomes before making code edits; if discovery indicates reuse of an existing inbound-trigger system, adjust file targets accordingly (step 14 is mandatory).
- Prefer minimal, product-complete changes: receive, validate signature, dedupe, normalize, persist binding, and dispatch. Avoid building a generic webhook platform unless discovery shows that is the canonical approach.
- If GitHub connector already stores secrets and supports webhook auto-registration, include only the integration wiring (verify during discovery and update steps).
- Keep the scope limited to GitHub-specific trigger support and the minimal UI to configure bindings in the workflow builder.
