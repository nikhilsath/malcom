Owner: backend/services
Responsibilities:
- Provide secure protection and unprotection of connector secret values used by connectors.
- Provide compact masking helpers for displaying secrets.

Public API:
- `get_connector_protection_secret(root_dir=None, db_path=None) -> str`
- `derive_connector_protection_key(protection_secret: str) -> bytes`
- `protect_connector_secret_value(value: str, protection_secret: str) -> str`
- `unprotect_connector_secret_value(value: str|None, protection_secret: str) -> str|None`
- `mask_connector_secret(value: str|None) -> str|None`

Owned DB tables: none

Inbound dependencies:
- `backend/services/helpers.py` (calls protection APIs)
- connector-related routes and services that need to protect/unprotect secret values

Allowed callers:
- Backend services that manage connectors and stored credentials

Test obligations:
- Unit tests validating protect/unprotect roundtrip and tamper detection
- Contract tests ensuring exported symbols and behavior remain stable

Migration rules:
- Backwards-incompatible changes to token format must include migration and compatibility wrappers in `helpers.py` during transition.
