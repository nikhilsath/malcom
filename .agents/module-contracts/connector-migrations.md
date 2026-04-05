# Module Contract: connector_migrations

**File:** `backend/services/connector_migrations.py`

## Responsibility
One-time migration helpers that promote legacy connector state from the `settings` table into the canonical `connectors` and `connector_auth_policies` tables.

## Exports

### Functions
- `ensure_legacy_connector_storage_migrated(connection)` — Entry point: migrates connectors and auth policy from legacy settings rows if present
- `_migrate_legacy_connectors_from_settings(connection)` — Moves connector records + auth policy from settings.connectors row
- `_read_connector_auth_policy_row(connection) -> dict | None` — Reads canonical auth policy row
- `_read_connector_auth_policy_setting(connection) -> dict | None` — Multi-path reader with fallback to legacy settings
- `_migrate_legacy_connector_auth_policy_setting(connection, settings_value, *, delete_connectors_row) -> dict` — Migrates legacy auth policy to canonical table

## Constraints
- Must not import `replace_stored_connector_records` or `write_connector_auth_policy` at module level (use lazy imports inside functions to avoid circular dependency with `connectors.py`)
- Imports `CONNECTOR_AUTH_POLICY_ROW_ID`, `CONNECTOR_AUTH_POLICY_SETTINGS_KEY`, `normalize_connector_auth_policy` from `connector_catalog`
- Migration functions must be idempotent (safe to call multiple times)
