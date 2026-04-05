# Module Contract: connector_catalog

**File:** `backend/services/connector_catalog.py`

## Responsibility
Provider catalog constants, metadata, and normalization helpers. Reads from `integration_presets` table when a DB connection is supplied; falls back to compile-time defaults otherwise.

## Exports

### Constants
- `DEFAULT_CONNECTOR_CATALOG` — List of provider presets (google, github, notion, trello)
- `DEFAULT_CONNECTOR_PROVIDER_METADATA` — Tuple of provider onboarding metadata dicts
- `SUPPORTED_CONNECTOR_PROVIDERS`, `SUPPORTED_CONNECTOR_AUTH_TYPES`, `SUPPORTED_CONNECTOR_STATUSES`
- `CONNECTOR_PROVIDER_CANONICAL_MAP`, `CONNECTOR_REQUEST_AUTH_TYPE_MAP`
- `CONNECTOR_STATUS_OPTIONS`, `CONNECTOR_ROTATION_INTERVAL_OPTIONS`, `CONNECTOR_CREDENTIAL_VISIBILITY_OPTIONS`
- `ACTIVE_STORAGE_CONNECTOR_STATUSES`, `CONNECTOR_AUTH_POLICY_ROW_ID`, `CONNECTOR_AUTH_POLICY_SETTINGS_KEY`

### Functions
- `canonicalize_connector_provider(provider) -> str | None` — Maps legacy provider IDs to canonical ones
- `build_connector_catalog(connection) -> list` — Returns catalog from DB or defaults
- `get_connector_preset(provider, *, connection) -> dict | None` — Looks up a single provider preset
- `get_connector_provider_metadata(provider) -> dict | None` — Returns provider onboarding metadata
- `get_default_connector_settings(connection) -> dict` — Default connector settings payload
- `normalize_connector_auth_policy(value) -> dict` — Validates/normalizes auth policy dict
- `normalize_connector_request_auth_type(auth_type) -> str` — Maps connector auth type to request auth type
- `build_connector_response_metadata() -> dict` — Returns UI-facing metadata for settings response

## Constraints
- Only imports from `backend.database` (fetch_all, fetch_one) and stdlib + typing
- Does not import from `connector_secrets`, `connectors`, or `connector_migrations`
- Falls back to compile-time constants when connection is None
