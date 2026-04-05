# Module Contract: log_table_schema

## Owner
backend/services team (log table subsystem)

## Responsibilities
- Identifier safety validation for SQL identifiers used in dynamic DDL
- Physical data-table naming (`log_data_<name>`)
- CREATE TABLE DDL generation for managed log-data tables
- Metadata persistence to `log_db_tables` and `log_db_columns`
- 404 helper for routing guards

## Public API

| Function | Signature | Notes |
|---|---|---|
| `assert_safe_identifier` | `(name: str) -> str` | Raises HTTP 422 on bad identifier |
| `data_table_name` | `(table_name: str) -> str` | Returns `"log_data_{table_name}"` |
| `build_create_table_sql` | `(data_table: str, columns: list[LogDbColumnDefinition]) -> str` | Returns DDL string |
| `create_log_table_ddl` | `(connection, data_table, columns) -> None` | Executes DDL via connection |
| `persist_log_table_metadata` | `(connection, *, table_id, name, description, columns, now) -> list[LogDbColumnResponse]` | Inserts table + column rows |
| `get_log_table_row_or_404` | `(connection, table_id: str) -> dict` | Fetches row or raises HTTP 404 |

## Example callsite

```python
from backend.services.log_table_schema import (
    assert_safe_identifier,
    create_log_table_ddl,
    data_table_name,
    persist_log_table_metadata,
)

assert_safe_identifier(payload.name)
physical_table = data_table_name(payload.name)
create_log_table_ddl(connection, physical_table, payload.columns)
col_responses = persist_log_table_metadata(
    connection, table_id=table_id, name=payload.name, description=payload.description,
    columns=payload.columns, now=now,
)
```

## Owned DB tables
- `log_db_tables` (write/create)
- `log_db_columns` (write/create)

## Inbound dependencies
- `backend.database.fetch_one`
- `backend.schemas.LogDbColumnDefinition`, `LogDbColumnResponse`
- `fastapi.HTTPException`, `fastapi.status`

## Outbound dependencies
None beyond stdlib.

## Allowed callers
- `backend/routes/log_tables.py`
- `backend/services/automation_execution.py` (log step writer)

## Test obligations
Required test file: `tests/test_log_tables_api.py`
Contract test: route→service boundary assertions via HTTP test client.

## Migration rules
Any column added to `log_db_tables` or `log_db_columns` must be reflected here and in `backend/database.py`.
