Execution steps

1. [x] [Route: backend]
Files: backend/database.py, backend/services/, backend/routes/, backend/services/workflow_builder.py, backend/routes/automations.py, backend/routes/connectors.py, backend/tool_registry.py, migrations/, tests/
Action: Discovery pass — verify the repository's current source-of-truth for automation triggers, connectors, inbound APIs, and any existing webhook/inbound delivery handling. Inspect these files/locations to determine whether a generic inbound-trigger system already exists and where trigger bindings are stored (DB table, settings, connectors table, or code-only). Produce a short discovery note at .github/tasks/open/TASK-022-discovery.md that records: (a) the canonical trigger storage (table/file), (b) where automation trigger types are registered, (c) existing inbound/post-receive routes, (d) recommended anchor points for a new GitHub-specific inbound route and service.
Note: Discovery completed — `.github/tasks/open/TASK-022-discovery.md` created with findings and recommendation to reuse `webhook_apis` + `webhook_api_events` and add `backend/services/github_webhook.py` with task-level acceptance criteria.
Completion check: `.github/tasks/open/TASK-022-discovery.md` exists and contains concrete statements naming the exact file(s) and table(s) (or "none") that currently hold trigger bindings, and a decision: "reuse X" or "create dedicated github_webhooks path".

2. [x] [Route: backend]
Files: backend/services/github_webhook.py
Action: Service API acceptance criteria & scaffolding — document public API, owner, dependencies, and required tests in task acceptance criteria and PR summary. Scaffold `backend/services/github_webhook.py` with placeholder functions and unit tests outline.
Completion check: scaffold exists and acceptance criteria explicitly cover API shape and test obligations.

3. [x] [Route: backend/db]
Files: backend/database.py, migrations/versions/, migrations/env.py (if present)
Action: Schema migration — extend existing durable storage for webhook deliveries to support GitHub delivery dedupe/audit. Preferred minimal change: add a `delivery_id TEXT` column to `webhook_api_events` and a unique index on it (when not null) to record `X-GitHub-Delivery`. Alternatively, create a dedicated `github_webhook_deliveries` table if separation is desired — document choice in the migration. Add a migration skeleton in `migrations/versions/` that adds the `delivery_id` column and index (or creates the `github_webhook_deliveries` table if chosen).
Completion check: `backend/database.py` updated (or commented) to reflect the storage choice and a new migration file exists under `migrations/versions/` that implements the schema change.

4. [x] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/services/__init__.py
Action: Add a service module `backend/services/github_webhook.py` with helper functions:
 - `verify_signature(headers, body, secret)` — GitHub HMAC-SHA256 verification helper (normalizes `sha256=` prefix).
 - `extract_delivery_id(headers)` — returns the `X-GitHub-Delivery` header value.
 - `normalize_github_event(payload, event_type)` — maps GitHub payloads to Malcom's internal event model.
 - `dispatch_normalized_event(connection, logger, normalized_event, metadata)` — delegates to existing automation dispatch (`execute_automation_definition` / runtime trigger queue) or calls into `receive_webhook_event` flow as appropriate.
Wire `backend/routes/apis.py` to import and call these helpers for GitHub deliveries.
Completion check: `backend/services/github_webhook.py` exists and `backend/routes/apis.py` imports and calls its verify/extract/normalize/dispatch helpers when processing GitHub webhook callbacks.

5. [x] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/automation_normalizers.py (or other normalizers)
Action: Implement payload normalization: add `normalize_github_event(payload, event_type)` producing Malcom's internal automation/event model (fields: source, repo, owner, event_type, ref/branch, affected_paths, actor, timestamp, raw_payload). The normalizer must convert core GitHub events (push, pull_request opened/closed/synchronized, etc.) into a consistent internal shape and return both the normalized event and metadata for matching configured bindings.
Completion check: `normalize_github_event` is present in `backend/services/github_webhook.py` (or referenced normalizer) and is called by the webhook processing flow prior to dispatch.

6. [x] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/database.py
Action: Implement idempotency/dedupe by recording `X-GitHub-Delivery` values on delivery processing. If using `webhook_api_events.delivery_id`, ensure uniqueness is enforced by migration and check for existing delivery_id to dedupe. The service must log and persist status for each delivery (accepted, rejected-signature, duplicate, dispatch-failed, dispatched).
Completion check: schema migration creates `delivery_id` support and `backend/services/github_webhook.py` (or `backend/services/apis.py`) inserts/checks delivery_id to prevent duplicate processing.

7. [x] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py, backend/database.py
Action: Add logging and auditability: ensure each delivery is logged with delivery id, signature check result, binding match result, and dispatch outcome. Persist delivery audit info in `webhook_api_events.delivery_id` (or `github_webhook_deliveries` if chosen) as implemented in step 3. Ensure logs are structured (logger name, level, delivery_id).
Completion check: new structured logging statements exist in `backend/services/github_webhook.py`/`backend/services/apis.py` and the audit insert/update occurs for every processed delivery.

8. [x] [Route: backend]
Files: backend/services/github_webhook.py, backend/services/apis.py
Action: Backend implementation & integration — implement `verify_signature`, `extract_delivery_id`, `normalize_github_event`, and integrate these into the existing `receive_webhook_event` flow in `backend/services/apis.py`. Implement dedupe check using `delivery_id` before dispatching.
Completion check: helpers implemented and imported by the receive flow; dedupe path returns expected duplicate handling without double-dispatch.

9. [x] [Route: backend/test]
Files: tests/test_github_webhooks.py
Action: Backend unit tests — add unit tests covering signature verification, delivery-id extraction, normalization, and dedupe logic. Tests must run as part of `scripts/test-precommit.sh` and be included in the PR.
Completion check: tests exist and pass locally in the workspace test environment.

10. [x] [Route: backend]
Files: backend/services/workflow_builder.py, backend/routes/automations.py, backend/schemas/automation.py
Action: Builder registration — add backend support for a `github` trigger type in the workflow-builder/automation trigger registration: expand the trigger registry/resolver so the builder API exposes `github` triggers and supports binding fields: `owner`, `repo`, `event_type`, `branch_filter`, `path_filter`, `secret` (or reference to stored secret). Ensure that runtime trigger matching uses normalized events and the `webhook_api_events` (or dedicated deliveries table) for binding lookup.
Completion check: the backend trigger registry contains an entry for `github` and the API that lists available trigger types returns `github` with the expected input schema.

11. [x] [Route: ui]
Files: ui/src/automation/trigger-settings-form.tsx, ui/src/automation/types.ts
Action: UI builder form — add a minimal GitHub trigger detail form capturing `owner`, `repo`, `events` (CSV), and optional `secret`. Ensure the form patches `trigger_config` fields in the same shape as backend expects.
Completion check: UI form fields exist and bind to `trigger_config.github_owner`, `trigger_config.github_repo`, `trigger_config.github_events`, `trigger_config.github_secret`.

Testing steps

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

Testing steps

1. [x] [Route: test]
Files: ui/src/automation/__tests__/, ui/e2e/
Action: UI tests — add unit tests for `trigger-settings-form.tsx` and related types, and add Playwright e2e test(s) under `ui/e2e/` as stubs. Run the UI unit tests and record the result.
Completion check: the new/updated unit tests for the GitHub trigger form exist under `ui/src/automation/__tests__/` and `npm test` (or the project's UI unit-test command) exits `0` for those tests; e2e stubs are present under `ui/e2e/`.

2. [x] [Route: test]
Files: tests/test_workflow_builder_service.py, tests/test_automations_api.py, tests/test_connectors_api.py (if updated), tests/test_connectors_for_builder.py (if updated)
Action: Test impact updates & CI — update affected backend tests identified in the Test Impact Review to account for the new `github` trigger type and normalization behavior. Run the repository precommit test script to validate changes.
Completion check: `scripts/test-precommit.sh` exits `0` (or the targeted pytest commands listed in the Test Impact Review pass) and the updated tests exist under their respective `tests/` paths.

Documentation review

1. [x] [Route: docs]
Files: docs/github-webhooks.md, README.md
Action: Documentation — add docs describing how to configure GitHub webhooks for Malcom: recommended webhook URL, which events to subscribe to, how to set the secret, an example push payload mapping to Malcom's fields, and instructions for using the workflow builder to create bindings. Include guidance on idempotency and delivery dedupe behavior.
Completion check: `docs/github-webhooks.md` exists and references the backend endpoint path and builder UI location.

GitHub update

1. [x] [Route: github]
Files: (list of files changed by implementation — to be filled by executor before commit)
Action: GitHub commit: stage only the files changed for this task and commit with a concise message like "Add GitHub webhook inbound endpoint, storage, normalization, and builder support" and push. Also move this task file from `.github/tasks/open/TASK-022-add-github-webhook-trigger.md` to `.github/tasks/closed/TASK-022-add-github-webhook-trigger.md` in the same commit per repo policy.
Completion check: A single commit exists on the branch that adds/updates only the task-relevant files and moves the task file to `.github/tasks/closed/`.
