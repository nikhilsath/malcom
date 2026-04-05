# Module Contract: log_table_import

## Owner
backend/services team (log table subsystem)

## Responsibilities
- Scalar value serialisation for imported row data
- Bulk row insertion into dynamic `log_data_*` tables

## Public API

| Function | Signature | Notes |
|---|---|---|
| `serialize_import_value` | `(value: Any) -> Any` | Coerces values to DB-safe scalars |
| `insert_log_table_rows` | `(connection, *, physical_table, column_names, rows, automation_id?) -> int` | Returns count inserted; raises HTTP 422 on unknown columns |

## Owned DB tables
Writes to dynamic `log_data_<name>` tables only.

## Inbound dependencies
- `backend.services.utils.utc_now_iso`
- `fastapi.HTTPException`, `fastapi.status`

## Allowed callers
- `backend/routes/log_tables.py`
- `backend/services/automation_execution.py` log-write step

## Test obligations
Required test file: `tests/test_log_tables_api.py`.

## Migration rules
Columns `row_id`, `automation_id`, `inserted_at` are system columns prepended to every insert; do not remove or rename them.
