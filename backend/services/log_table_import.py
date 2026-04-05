"""Log table import helpers: row serialisation and bulk insertion."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from backend.services.utils import utc_now_iso


def serialize_import_value(value: Any) -> Any:
    """Coerce *value* to a DB-safe scalar type."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def insert_log_table_rows(
    connection: Any,
    *,
    physical_table: str,
    column_names: list[str],
    rows: list[dict[str, Any]],
    automation_id: str = "dataset_import",
) -> int:
    """
    Insert *rows* into *physical_table*.

    Returns the count of rows inserted. Raises HTTP 422 if a row contains
    columns not present in *column_names*.
    """
    defined_columns = set(column_names)
    inserted = 0
    for row in rows:
        unexpected = [c for c in row if c not in defined_columns]
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Imported rows contain unknown columns: "
                    + ", ".join(sorted(unexpected))
                    + "."
                ),
            )

        row_id = f"logrow_{uuid4().hex[:12]}"
        inserted_at = utc_now_iso()
        row_col_names = ["row_id", "automation_id", "inserted_at", *row.keys()]
        row_values = [
            row_id,
            automation_id,
            inserted_at,
            *(serialize_import_value(v) for v in row.values()),
        ]
        placeholders = ", ".join(["?"] * len(row_values))
        connection.execute(
            f"INSERT INTO {physical_table} ({', '.join(row_col_names)}) VALUES ({placeholders})",
            row_values,
        )
        inserted += 1

    return inserted
