Discovery for TASK-022: GitHub webhook trigger

Date: 2026-04-06

Summary decision: reuse existing generic webhook infrastructure (`webhook_apis`, `webhook_api_events`, and `receive_webhook_event`) and extend it for GitHub specifics. Create a small service module `backend/services/github_webhook.py` for normalization and delivery-id dedupe, with task-level acceptance criteria in the implementation task.

Findings (concrete file/table locations):

- Canonical trigger storage and delivery history:
  - `backend/database.py` defines tables: `inbound_apis`, `inbound_api_events`, `webhook_apis`, `webhook_api_events` (use these as the canonical storage locations). See `CREATE TABLE IF NOT EXISTS webhook_apis` and `CREATE TABLE IF NOT EXISTS webhook_api_events`.

- Where automation trigger types are registered:
  - `backend/services/workflow_builder.py` — `AUTOMATION_TRIGGER_TYPE_OPTIONS` (currently includes `inbound_api`, `manual`, `schedule`, `smtp_email`). Add `github` here if exposing a distinct trigger type in the builder.
  - `backend/routes/automations.py` reads and writes `automations.trigger_type` and `trigger_config_json`. Validation for inbound triggers exists in `_ensure_inbound_trigger_reference_exists` (it already accepts rows in `inbound_apis` or `webhook_apis`). See `backend/routes/automations.py`.
  - Automations persisted in `automations` table (`backend/database.py`) with `trigger_type` and `trigger_config_json` are the runtime source-of-truth for bindings.

- Existing inbound/post-receive routes and dispatch logic:
  - Route: `POST /api/v1/webhooks/callback/{callback_path:path}` implemented in `backend/routes/apis.py` (function `receive_webhook_callback`). This code looks up `webhook_apis` by `callback_path` and calls `receive_webhook_event` in `backend/services/apis.py`.
  - Service: `backend/services/apis.py` contains `receive_webhook_event(...)` which: verifies verification token, verifies HMAC signatures (using `signing_secret` and `signature_header` from `webhook_apis`), infers event name, logs into `webhook_api_events`, and calls `_execute_matching_webhook_automations(...)` to dispatch matching automations. This function currently selects automations WHERE `trigger_type = 'inbound_api'` and matches `trigger_config.inbound_api_id == api_id` — note: automations with `trigger_type == 'inbound_api'` are used to reference both `inbound_apis` and `webhook_apis` (see `_ensure_inbound_trigger_reference_exists` which accepts either table).

- Existing connector/secret handling and GitHub-specific support:
  - `backend/routes/connectors.py` and `backend/services/connector_repositories.py` include GitHub connector helpers (listing repos, inspecting scopes). However, connector rows are separate from `webhook_apis` and not currently used as the webhook inbound trigger store.
  - `receive_webhook_event` already supports HMAC-SHA256 signatures and allows configurable `signature_header` (it strips `sha256=` prefix if present). Therefore verifying `x-hub-signature-256` with a stored `signing_secret` and `signature_header='x-hub-signature-256'` will work without additional signature code.

Recommended anchor points for implementing GitHub support (reuse-first):

1. Reuse `webhook_apis` + `webhook_api_events` for durable binding and event history. Do not create a parallel `github_webhook_bindings` unless strong, documented justification exists. Instead, add a `delivery_id` column to `webhook_api_events` (and a unique index on it when present) to record `X-GitHub-Delivery` for dedupe/audit, or create a small `github_webhook_deliveries` table if you prefer a separate audit table — either approach is acceptable but prefer extending `webhook_api_events` for minimal footprint.

2. Route: reuse `POST /api/v1/webhooks/callback/{callback_path:path}` in `backend/routes/apis.py`. This already delegates to `receive_webhook_event` in `backend/services/apis.py` which performs verification and dispatch. Modify or extend `receive_webhook_event` (or add a wrapper) to capture `X-GitHub-Delivery` and call GitHub normalizer before dispatch.

3. Service: add `backend/services/github_webhook.py` to implement:
   - `verify_signature(headers, body, secret)` (optional; existing `receive_webhook_event` supports SHA256 verification via `signing_secret` but a helper centralizes GitHub specifics),
   - `extract_delivery_id(headers)` returning `X-GitHub-Delivery`,
   - `normalize_github_event(payload, event_type)` that maps GitHub event shapes (push, pull_request, etc.) into Malcom's internal event model, returning (normalized_event, metadata_for_matching).
   - `dispatch_normalized_event(normalized_event)` which delegates into the existing automation dispatch path (`execute_automation_definition` or `_execute_matching_webhook_automations`) via the canonical RuntimeTrigger flow.

4. Workflow-builder metadata: add `github` to `AUTOMATION_TRIGGER_TYPE_OPTIONS` in `backend/services/workflow_builder.py` (and update `backend/schemas`/`backend/schemas/automation.py` if needed) so the UI builder can present a `GitHub` trigger type with expected config fields (`owner`, `repo`, `event_type`, `branch_filter`, `path_filter`, `secret_id` or `secret_value`). Alternatively, reuse `inbound_api` and expose `webhook` endpoint creation flows in the UI — but adding `github` produces a clearer UX.

5. Task acceptance criteria: capture public API (functions), owner, dependencies (uses `receive_webhook_event`, reads/writes `webhook_api_events`), and required tests directly in the implementation task and PR summary.

Tests / migration guidance:
- Migration: add a migration to extend `webhook_api_events` with a `delivery_id TEXT` column and an index `CREATE UNIQUE INDEX IF NOT EXISTS webhook_api_events_delivery_id_idx ON webhook_api_events(delivery_id)` (or create `github_webhook_deliveries` as an alternative if preferred). Place migration under `migrations/versions/`.
- Tests: unit tests should cover signature verification (existing code already supports HMAC-SHA256), delivery dedupe (assert duplicate `X-GitHub-Delivery` is idempotent), normalization of push/pull_request payloads, and an end-to-end dispatch using the existing `receive_webhook_event` flow.

Conclusion / Decision:
- Decision: reuse the existing `webhook_apis` and `webhook_api_events` and `receive_webhook_event` path as the canonical anchor points; implement `backend/services/github_webhook.py` for GitHub-specific normalization and delivery-id handling.

Next steps (executor):
1. Add `backend/services/github_webhook.py` with normalization, delivery-id extraction, and a dispatch helper that integrates with `receive_webhook_event` dispatch.
2. Add migration to extend `webhook_api_events` (or add `github_webhook_deliveries`) for delivery dedupe/audit.
3. Add minimal tests under `tests/test_github_webhooks.py`.

Discovery complete.
