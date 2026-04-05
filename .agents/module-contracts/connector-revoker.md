# Module Contract: connector_revoker

**File:** `backend/services/connector_revoker.py`

## Responsibility
Provider-specific connector revoke lifecycle.  Owns the full revoke-connector
workflow: record lookup, credential extraction, per-provider upstream token
revocation, credential clearing, persistence, and sanitised result production.

## Exports

### Functions
- `revoke_connector(*, connection, connector_id, protection_secret) -> tuple[str, dict]`
  — Revokes the upstream token (where supported), clears all local credential fields,
  marks the record as `revoked`, persists, and returns `(message, sanitised_record_dict)`.

## Signature Contract
```
revoke_connector(
    *,
    connection: Any,            # live DB connection
    connector_id: str,          # existing connector row ID
    protection_secret: str,     # workspace credential encryption key
) -> tuple[str, dict[str, Any]]
    # (human-readable message, sanitised connector record dict)
```

## Inbound Dependencies
| Module | Symbols used |
|--------|--------------|
| `backend.services.connector_catalog` | `canonicalize_connector_provider`, `_provider_display_name` |
| `backend.services.connector_google_oauth_client` | `revoke_google_token` |
| `backend.services.connector_oauth_provider_clients` | `revoke_notion_token`, `revoke_trello_token` |
| `backend.services.connector_secrets` | `extract_connector_secret_map` |
| `backend.services.connectors` | `find_stored_connector_record`, `save_connector_record`, `sanitize_connector_record_for_response` |
| `backend.services.utils` | `utc_now_iso` |

## Constraints
- No FastAPI `Request` object or route-level concerns; all parameters are plain Python values.
- Raises `HTTPException 404` when the connector is not found.
- Does **not** import from `backend.routes.*`.
- All credential-clearing logic and provider dispatch must live here, not in the route.
- The constant `_CLEARED_CREDENTIAL_FIELDS` defines the canonical set of fields zeroed on revoke.

## Caller Contract
Routes must:
1. Extract `connection` and `protection_secret` from the request context.
2. Call `revoke_connector(connection=…, connector_id=…, protection_secret=…)`.
3. Shape the returned tuple into a `ConnectorActionResponse(ok=True, …)` and return it.

No provider-specific logic is permitted in routes.

## Test Obligations
- Unit tests: `tests/test_connector_revoker_service.py`
  - All four named providers (google, github, notion, trello) — complete-credentials and
    partial-credentials paths.
  - 404 when connector not found.
  - Credential fields are cleared after revocation.
  - Record status becomes `"revoked"` after call.
- Contract tests: `tests/test_connector_revoker_contract.py`
  - Route calls `revoke_connector` once per POST `/revoke` request.
  - Route does not import or invoke any provider-specific revoke function directly.
  - Return value is correctly shaped into `ConnectorActionResponse`.
