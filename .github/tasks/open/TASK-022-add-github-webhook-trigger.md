Execution steps

1. [x] [Route: backend]
Files: backend/database.py, backend/services/, backend/routes/, backend/services/workflow_builder.py, backend/routes/automations.py, backend/routes/connectors.py, backend/tool_registry.py, migrations/, tests/
Action: Discovery pass — verify the repository's current source-of-truth for automation triggers, connectors, inbound APIs, and any existing webhook/inbound delivery handling. Inspect these files/locations to determine whether a generic inbound-trigger system already exists and where trigger bindings are stored (DB table, settings, connectors table, or code-only). Produce a short discovery note at .github/tasks/open/TASK-022-discovery.md that records: (a) the canonical trigger storage (table/file), (b) where automation trigger types are registered, (c) existing inbound/post-receive routes, (d) recommended anchor points for a new GitHub-specific inbound route and service.
Note: Discovery completed — `.github/tasks/open/TASK-022-discovery.md` created with findings and recommendation to reuse `webhook_apis` + `webhook_api_events` and add `backend/services/github_webhook.py` with task-level acceptance criteria.
Completion check: `.github/tasks/open/TASK-022-discovery.md` exists and contains concrete statements naming the exact file(s) and table(s) (or "none") that currently hold trigger bindings, and a decision: "reuse X" or "create dedicated github_webhooks path".
Note: If discovery determines a new service/module is required, include explicit task acceptance criteria for module owner, public API, dependencies, and tests in the same PR that implements the service.

12. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/services/workflow_builder.py, backend/database.py
Action: Add logging and auditability: ensure each delivery is logged with delivery id, signature check result, binding match result, and dispatch outcome. Persist delivery audit info in `webhook_api_events.delivery_id` (or `github_webhook_deliveries` if chosen) as implemented in step 4. Ensure logs are structured (logger name, level, delivery_id).
Completion check: new structured logging statements exist in `backend/services/github_webhook.py`/`backend/services/apis.py` and the audit insert/update occurs for every processed delivery.

3. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/services/__init__.py
Action: Add a service module `backend/services/github_webhook.py` with functions:
- `verify_signature(headers, body, secret)` — GitHub HMAC-SHA256 verification helper (normalizes `sha256=` prefix).
- `extract_delivery_id(headers)` — returns the `X-GitHub-Delivery` header value.
- `normalize_github_event(payload, event_type)` — maps GitHub payloads to Malcom's internal event model.
- `dispatch_normalized_event(connection, logger, normalized_event, metadata)` — delegates to existing automation dispatch (`execute_automation_definition` / runtime trigger queue) or calls into `receive_webhook_event` flow as appropriate.
Wire `backend/routes/apis.py` to import and call these helpers for GitHub deliveries.
Completion check: `backend/services/github_webhook.py` exists and `backend/routes/apis.py` imports and calls its verify/extract/normalize/dispatch helpers when processing GitHub webhook callbacks.

Additional completion check: The task and PR summary explicitly document service owner, public API, dependencies, and test obligations. Include unit + contract tests in the same PR and verify via `scripts/test-module.sh github_webhook` or the nearest relevant module name.

4. [ ] [Route: backend/db]
Files: backend/database.py, migrations/versions/, migrations/env.py (if present)
Action: Extend existing durable storage for webhook deliveries to support GitHub delivery dedupe/audit. Preferred minimal change: add a `delivery_id TEXT` column to `webhook_api_events` and a unique index on it (when not null) to record `X-GitHub-Delivery`. Alternatively, create a dedicated `github_webhook_deliveries` table if separation is desired — document choice in the migration.
Add a migration skeleton in `migrations/versions/` that adds the `delivery_id` column and index (or creates the `github_webhook_deliveries` table if chosen).
Completion check: `backend/database.py` updated (or commented) to reflect the storage choice and a new migration file exists under `migrations/versions/` that implements the schema change.

Note: Ensure the migration and any new table ownership are reflected in task acceptance criteria and README/AGENTS schema documentation so table ownership follows R-SOT-001.

5. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/automation_normalizers.py (or other normalizers)
Action: Implement payload normalization: add `normalize_github_event(payload, event_type)` producing Malcom's internal automation/event model (fields: source, repo, owner, event_type, ref/branch, affected_paths, actor, timestamp, raw_payload). The normalizer must convert core GitHub events (push, pull_request opened/closed/synchronized, etc.) into a consistent internal shape and return both the normalized event and metadata for matching configured bindings.
Completion check: `normalize_github_event` is present in `backend/services/github_webhook.py` (or referenced normalizer) and is called by the webhook processing flow prior to dispatch.

6. [ ] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/database.py
Action: Implement idempotency/dedupe by recording `X-GitHub-Delivery` values on delivery processing. If using `webhook_api_events.delivery_id`, ensure uniqueness is enforced by migration and check for existing delivery_id to dedupe. The service must log and persist status for each delivery (accepted, rejected-signature, duplicate, dispatch-failed, dispatched).
Completion check: schema migration creates `delivery_id` support and `backend/services/github_webhook.py` (or `backend/services/apis.py`) inserts/checks delivery_id to prevent duplicate processing.

7. [ ] [Route: backend]
Files: backend/services/workflow_builder.py, backend/routes/automations.py, backend/schemas/automation.py
Action: Add backend support for a `github` trigger type in the workflow-builder/automation trigger registration: expand the trigger registry/resolver so the builder API exposes `github` triggers and supports binding fields: `owner`, `repo`, `event_type`, `branch_filter`, `path_filter`, `secret` (or reference to stored secret). Ensure that runtime trigger matching uses normalized events and the `webhook_api_events` (or dedicated deliveries table) for binding lookup.
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

Additional completion check: Tests and explicit task acceptance criteria are added in the same PR and the module-scoped tests run under `scripts/test-module.sh github_webhook` (or the appropriate module name) as part of the PR validation.

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

14. [x] [Route: backend]
Files: .github/tasks/open/TASK-022-discovery.md
Action: Discovery chose to reuse existing inbound webhook infrastructure. Downstream steps (2–13) have been updated to reference `backend/routes/apis.py`, `webhook_apis`, `webhook_api_events`, and `backend/services/github_webhook.py` as the integration points.
Completion check: `.github/tasks/open/TASK-022-discovery.md` contains the reuse decision and this task file's steps 2–13 have been updated to reference the reuse locations.

15. [ ] [Route: github]
Files: (list of files changed by implementation — to be filled by executor before commit)
Action: GitHub commit: stage only the files changed for this task and commit with a concise message like "Add GitHub webhook inbound endpoint, storage, normalization, and builder support" and push. Also move this task file from `.github/tasks/open/TASK-022-add-github-webhook-trigger.md` to `.github/tasks/closed/TASK-022-add-github-webhook-trigger.md` in the same commit per repo policy.
Completion check: A single commit exists on the branch that adds/updates only the task-relevant files and moves the task file to `.github/tasks/closed/`.

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
Execution steps (reordered and aligned to repository policies)

Overview: follow a reuse-first approach (discovery completed) and ensure migrations, tests, and docs accompany behavior changes per repository policy. Each implementation stage must include unit tests and migration/script updates where applicable.

1. Discovery (completed)
Files: .github/tasks/open/TASK-022-discovery.md
Action: Confirmed reuse of existing inbound webhook infrastructure: `backend/routes/apis.py`, `webhook_apis`, `webhook_api_events`. Decision recorded in discovery file.
Completion check: discovery file exists and names canonical files/tables and the recommended integration points.

2. Service API acceptance criteria & scaffolding (completed)
Files: backend/services/github_webhook.py
Action: Document public API, owner, dependencies, and required tests in task acceptance criteria and PR summary. Scaffold `backend/services/github_webhook.py` with placeholder functions and unit tests outline.
Completion check: scaffold exists and acceptance criteria explicitly cover API shape and test obligations.

3. Schema migration (completed)
Files: backend/migrations/versions/0002_add_webhook_delivery_id.py, backend/database.py (docs/notes)
Action: Add a migration to persist `delivery_id` on `webhook_api_events` (or document alternate table choice). Ensure migration is defensive across dialects and includes index for dedupe. Update schema docs/AGENTS notes describing the canonical ownership (R-SOT-001).
Completion check: migration file exists and `backend/database.py` or AGENTS notes reference the storage choice.

4. Backend implementation & integration (completed)
Files: backend/services/github_webhook.py, backend/services/apis.py
Action: Implement `verify_signature`, `extract_delivery_id`, `normalize_github_event`, and integrate these into the existing `receive_webhook_event` flow in `backend/services/apis.py`. Implement dedupe check using `delivery_id` before dispatching.
Completion check: helpers implemented and imported by the receive flow; dedupe path returns expected duplicate handling without double-dispatch.

5. Logging & audit (completed)
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/migrations/versions/0002_add_webhook_delivery_id.py
Action: Ensure each delivery is logged with structured fields (`delivery_id`, `signature_result`, `dispatch_status`) and that audit info is persisted (via `webhook_api_events.delivery_id` or an audit table). Logging statements must be consistent and discoverable in logs.
Completion check: structured logging statements exist and audit persistence occurs for processed deliveries.

6. Backend unit tests (completed)
Files: tests/test_github_webhooks.py
Action: Add unit tests covering signature verification, delivery-id extraction, normalization, and dedupe logic. Tests must run as part of `scripts/test-precommit.sh` and be included in the PR.
Completion check: tests exist and pass locally in the workspace test environment.

7. Builder registration (completed)
Files: backend/schemas/automation.py, backend/services/workflow_builder.py
Action: Register `github` as an available trigger type in the backend builder metadata and define the expected trigger_config fields (`github_owner`, `github_repo`, `github_events`, `github_secret` or secret reference). Ensure API that serves builder metadata includes `github`.
Completion check: backend builder metadata exposes `github` and the UI can receive it via existing builder endpoints.

8. UI builder form (completed)
Files: ui/src/automation/trigger-settings-form.tsx, ui/src/automation/types.ts
Action: Add a minimal GitHub trigger detail form capturing `owner`, `repo`, `events` (CSV), and optional `secret`. Ensure the form patches `trigger_config` fields in the same shape as backend expects.
Completion check: UI form fields exist and bind to `trigger_config.github_owner`, `trigger_config.github_repo`, `trigger_config.github_events`, `trigger_config.github_secret`.

9. UI unit tests (in-progress)
Files: ui/src/automation/__tests__/ (add tests for trigger form)
Action: Add unit tests for the new form component and ensure they run under the project's UI test harness. Keep tests small and focused on serialization and patch behavior.
Completion check: unit tests added and runnable locally; status: in-progress.

10. UI e2e tests (not-started)
Files: ui/e2e/github-trigger.spec.ts
Action: Add Playwright test(s) that exercise creating a `github` trigger via the builder picker → detail flow and assert the backend API is called with the expected payload (use mocked backend or network interception per repo conventions).
Completion check: e2e test exists under `ui/e2e/` and can run with the repo's e2e tooling.

11. Documentation (not-started)
Files: docs/github-webhooks.md, README.md, backend/AGENTS.md (if policy note required)
Action: Document endpoint URL, recommended GitHub event list, secret guidance, idempotency behavior, and builder UI usage. Cross-link to automation builder docs and connector/secret management docs if applicable.
Completion check: docs/github-webhooks.md created and linked from README or AGENTS notes.

12. Test impact updates & CI (not-started)
Files: tests/test_workflow_builder_service.py, tests/test_automations_api.py, other impacted tests discovered in discovery
Action: Update and run affected tests identified in the Test Impact Review. Ensure `scripts/test-precommit.sh` succeeds locally.
Completion check: affected tests updated and CI-local precommit test passes.

13. Commit and close task (not-started)
Files: (list created at commit time)
Action: Stage only task-relevant files, commit with a focused message, and move this task file from `.github/tasks/open/` to `.github/tasks/closed/` in the same commit per repo policy.
Completion check: commit contains only relevant files and the task file is moved to `.github/tasks/closed/`.

Notes / enforcement
- Each behavior-changing backend change must include unit tests and schema migration in the same PR (R-TEST-008, R-DB-002).
- Do not hand-edit generated UI artifacts; add new UI source files under `ui/src/` and update e2e coverage under `ui/e2e/` (R-GEN-001, R-TEST-005).
- Update `AGENTS.md` or `backend/AGENTS.md` only if repository policy requires noting new trigger types (R-POLICY-001).

Test Impact Review (summary)
- `tests/test_workflow_builder_service.py`: update to include `github` trigger registration checks.
- `tests/test_automations_api.py`: add assertions for inbound normalized dispatch.
- `tests/test_connectors_for_builder*.py`: review only if connector/secret management is used.
- UI unit tests: add focused tests for trigger form serialization.

Executor guidance: after making code edits, run `scripts/test-precommit.sh` locally and include the passing results in the PR description. When committing, follow the GitHub update workflow in AGENTS.md.
