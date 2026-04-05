Owner: backend/services
Responsibilities:
- Encapsulate provider-specific connector test logic (Google, GitHub, Notion, Trello, and generic credential heuristics).

Public API:
- `test_connector_record(record: dict) -> tuple[bool, str, dict]` — returns (ok, message, updated_record).

Owned DB tables:
- `connectors` (logical owner for connector status/last_tested timestamps)

Inbound dependencies:
- `backend/services/connector_health`
- `backend/services/support`

Allowed callers:
- `backend/routes/connectors.py`
- automated health-check services

Test obligations:
- Unit tests covering each provider path and expiry/credential heuristics
- Contract test ensuring the route saves returned record fields and response shaping is correct

Example callsite:
```
ok, message, updated_record = test_connector_record(record)
record = save_connector_record(connection, updated_record, protection_secret=protection_secret)
```
