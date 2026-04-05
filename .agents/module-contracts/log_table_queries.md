# Module Contract: log_table_queries

## Owner
backend/services team (log table subsystem)

## Responsibilities
- Listing physical data-table columns (via `information_schema`)
- Building `LogDbTableSummary` and `LogDbColumnResponse` view objects
- Fetching rows and total counts with graceful error fallback

## Public API

| Function | Signature | Notes |
|---|---|---|
| `list_data_table_columns` | `(connection, physical_table: str) -> list[str]` | Raw column names from information_schema |
| `build_table_summary` | `(row: dict, connection) -> LogDbTableSummary` | Builds summary with live row count |
| `build_column_response` | `(row: dict) -> LogDbColumnResponse` | Deserialises a log_db_columns row |
| `fetch_log_table_columns` | `(connection, table_id, *, physical_table, logger?) -> list[str]` | With fallback to log_db_columns |
| `fetch_log_table_rows` | `(connection, *, table_id, physical_table, limit?, logger?) -> list[dict]` | Returns empty list on error |
| `fetch_log_table_total` | `(connection, *, table_id, physical_table, logger?) -> int` | Returns 0 on error |

## Owned DB tables
Reads from: `log_db_tables`, `log_db_columns`, dynamic `log_data_*` tables.

## Inbound dependencies
- `backend.database.fetch_all`, `fetch_one`
- `backend.schemas.LogDbColumnResponse`, `LogDbTableSummary`
- `backend.services.log_table_schema.data_table_name`

## Allowed callers
- `backend/routes/log_tables.py`

## Test obligations
Required test file: `tests/test_log_tables_api.py`

## Migration rules
Changes to the `log_db_tables` or `log_db_columns` columns used here must be aligned with `persist_log_table_metadata` in `log_table_schema.py`.
