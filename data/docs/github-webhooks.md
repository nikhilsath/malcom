# GitHub Webhooks

Endpoint: `/api/v1/webhooks/<id>` (use the builder to create a webhook API resource)

Overview
- Malcom accepts inbound GitHub webhooks via the existing webhook API infrastructure (`webhook_apis`, `webhook_api_events`).
- The GitHub integration normalizes core event types (`push`, `pull_request`) into a consistent internal shape used by automation triggers.

Recommended GitHub webhook settings
- Payload URL: `<MALCOM_BASE_URL>/api/v1/webhooks/<callback_path>`
- Content type: `application/json`
- Secret: set a webhook secret and enter the same secret in the builder/webhook resource so Malcom can verify HMAC-SHA256 signatures.
- Events: subscribe to the specific events you need (e.g. `push`, `pull_request`).

Idempotency and dedupe
- Malcom records `X-GitHub-Delivery` (if present) in `webhook_api_events.delivery_id` to prevent duplicate processing.
- A migration was added to allow this column; delivery dedupe is attempted when the header is present.

Builder integration
- The workflow builder exposes a `GitHub` trigger type with fields: `github_owner`, `github_repo`, `github_events`, and optional `github_secret`.
- At runtime, normalized events are matched against stored automations' trigger_config values.

Troubleshooting
- If webhooks are ignored, verify the configured event filter, verification token, and signing secret match what GitHub is sending.
- Check `webhook_api_events` rows for `status` values: `invalid_verification`, `invalid_signature`, `ignored`, `duplicate`, or `accepted`.

API behavior
- When signature verification or verification token fails, Malcom logs the event and returns 401.
- Duplicate deliveries return a `duplicate` status and are not dispatched again.

See also
- `backend/services/github_webhook.py` — normalization and helpers
- `backend/services/apis.py` — receive and dispatch flow
