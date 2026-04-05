Owner: backend/services
Responsibilities:
- Provide connector provider catalog, presets and default connector settings.
- Resolve canonical provider ids and build runtime catalog from `integration_presets` DB table.

Public API:
- `build_connector_catalog(connection=None) -> list[dict]`
- `get_connector_preset(provider: str, connection=None) -> dict|None`
- `get_default_connector_settings() -> dict`
- `canonicalize_connector_provider(provider: str|None) -> str|None`

Owned DB tables:
- `integration_presets` (reads only)

Inbound dependencies:
- `backend/services/helpers.py` (uses catalog and presets)
- Routes that surface connector catalog and defaults

Allowed callers:
- Backend services and routes that need connector catalog/presets

Test obligations:
- Unit tests for catalog building, deduplication, and preset mapping
- Contract tests for public API stability

Migration rules:
- New provider presets must be added to `integration_presets` seed step and reflected in contract tests.
