# Module Contract: connector_tester

**File:** `backend/services/connector_tester.py`

## Responsibility
Provider-specific connector health-test lifecycle.  Owns the full test-connector
workflow: record lookup, credential extraction, per-provider upstream probe,
status/timestamp update, persistence, and sanitised result production.

## Exports

### Functions
- `test_connector(*, connection, connector_id, protection_secret) -> tuple[bool, str, dict]`
  — Probes the connector's upstream service, updates and saves the record, and returns
  `(ok, message, sanitised_record_dict)`.

## Signature Contract
```
test_connector(
    *,
    connection: Any,            # live DB connection
    connector_id: str,          # existing connector row ID
    protection_secret: str,     # workspace credential encryption key
) -> tuple[bool, str, dict[str, Any]]
    # (ok, human-readable message, sanitised connector record dict)
```

## Inbound Dependencies
| Module | Symbols used |
|--------|--------------|
| `backend.runtime` | `parse_iso_datetime` |
| `backend.services.connector_catalog` | `canonicalize_connector_provider`, `_provider_display_name` |
| `backend.services.connector_health` | `_probe_google_access_token`, `_probe_github_access_token`, `_probe_notion_access_token`, `_probe_trello_credentials` |
| `backend.services.connector_secrets` | `extract_connector_secret_map` |
| `backend.services.connectors` | `find_stored_connector_record`, `save_connector_record`, `sanitize_connector_record_for_response` |
| `backend.services.utils` | `utc_now_iso` |

## Constraints
- No FastAPI `Request` object or route-level concerns; all parameters are plain Python values.
- Raises `HTTPException 404` when the connector is not found.
- Propagates `HTTPException 502` raised by provider probe functions (network failures).
- Does **not** import from `backend.routes.*`.
- All provider dispatch logic must live here, not in the route.

## Caller Contract
Routes must:
1. Extract `connection` and `protection_secret` from the request context.
2. Call `test_connector(connection=…, connector_id=…, protection_secret=…)`.
3. Shape the returned tuple into a `ConnectorActionResponse` and return it.

No provider-specific logic is permitted in routes.

## Test Obligations
- Unit tests: `tests/test_connector_tester_service.py`
  - All four named providers (google, github, notion, trello) — success and missing-credential paths.
  - Revoked connector short-circuit.
  - Expired token short-circuit.
  - Generic credential-complete and credential-missing fallbacks.
  - 404 when connector not found.
- Contract tests: `tests/test_connector_tester_contract.py`
  - Route calls `test_connector` once per POST `/test` request.
  - Route does not import or invoke any provider probe directly.
  - Return value is correctly shaped into `ConnectorActionResponse`.
