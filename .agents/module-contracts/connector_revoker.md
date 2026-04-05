Owner: backend/services
Responsibilities:
- Encapsulate provider-specific revoke lifecycle actions for connectors (Google, Notion, Trello, GitHub fallback messaging).

Public API:
- `revoke_connector_record(record: dict) -> tuple[dict, str]` — performs provider revoke side-effects, updates status fields, and returns (updated_record, message).

Owned DB tables:
- `connectors` (logical owner for connector lifecycle updates)

Inbound dependencies:
- `backend/services/connector_google_oauth_client`
- `backend/services/connector_oauth_provider_clients`
- `backend/services/support`

Allowed callers:
- `backend/routes/connectors.py`
- other backend services that manage connector lifecycle

Test obligations:
- Unit tests verifying per-provider branches (test cases for google, github, notion, trello, unknown provider)
- Contract test ensuring `routes/connectors.py` delegates to this module and that returned record shape is persisted by routes.

Example callsite:
```
updated_record, message = revoke_connector_record(record)
record = save_connector_record(connection, updated_record, protection_secret=protection_secret)
```
