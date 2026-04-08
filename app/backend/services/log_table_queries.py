"""Log table query helpers: column listing, row fetching, and response serialisation."""

from __future__ import annotations

import logging
from typing import Any

from backend.database import fetch_all, fetch_one
from backend.schemas import LogDbColumnResponse, LogDbTableSummary
from backend.services.log_table_schema import data_table_name


def list_data_table_columns(connection: Any, physical_table: str) -> list[str]:
    """Return the ordered column names of *physical_table* from information_schema."""
    rows = fetch_all(
        connection,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ?
        ORDER BY ordinal_position
        """,
        (physical_table,),
    )
    return [r["column_name"] for r in rows]


def build_table_summary(row: dict[str, Any], connection: Any) -> LogDbTableSummary:
    """Build a LogDbTableSummary from a log_db_tables row."""
    physical_table = data_table_name(row["name"])
    try:
        count_row = fetch_one(connection, f"SELECT COUNT(*) AS cnt FROM {physical_table}", ())
        row_count = count_row["cnt"] if count_row else 0
    except Exception:
        row_count = 0
    return LogDbTableSummary(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        row_count=row_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def build_column_response(row: dict[str, Any]) -> LogDbColumnResponse:
    """Build a LogDbColumnResponse from a log_db_columns row."""
    return LogDbColumnResponse(
        id=row["id"],
        table_id=row["table_id"],
        column_name=row["column_name"],
        data_type=row["data_type"],
        nullable=bool(row["nullable"]),
        default_value=row.get("default_value"),
        position=row["position"],
        created_at=row["created_at"],
    )


def fetch_log_table_columns(connection: Any, table_id: str, *, physical_table: str, logger: Any = None) -> list[str]:
    """
    Return column names for *physical_table*, falling back to log_db_columns on error.

    Logs a warning via *logger* when the information_schema path fails.
    """
    try:
        return list_data_table_columns(connection, physical_table)
    except Exception as error:
        if logger is not None:
            from backend.services.support import write_application_exception_log  # lazy to avoid circular

            write_application_exception_log(
                logger,
                logging.WARNING,
                "log_table_columns_fallback",
                error=error,
                table_id=table_id,
                data_table=physical_table,
            )
        col_rows = fetch_all(
            connection,
            "SELECT column_name FROM log_db_columns WHERE table_id = ? ORDER BY position",
            (table_id,),
        )
        return ["row_id", "automation_id", "inserted_at"] + [c["column_name"] for c in col_rows]


def fetch_log_table_rows(
    connection: Any,
    *,
    table_id: str,
    physical_table: str,
    limit: int = 100,
    logger: Any = None,
) -> list[dict[str, Any]]:
    """Fetch up to *limit* rows from *physical_table*, returning an empty list on error."""
    try:
        rows = fetch_all(
            connection,
            f"SELECT * FROM {physical_table} ORDER BY inserted_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]
    except Exception as error:
        if logger is not None:
            from backend.services.support import write_application_exception_log

            write_application_exception_log(
                logger,
                logging.WARNING,
                "log_table_rows_query_failed",
                error=error,
                table_id=table_id,
                data_table=physical_table,
                limit=limit,
            )
        return []


def fetch_log_table_total(
    connection: Any,
    *,
    table_id: str,
    physical_table: str,
    logger: Any = None,
) -> int:
    """Return total row count for *physical_table*, or 0 on error."""
    try:
        count_row = fetch_one(connection, f"SELECT COUNT(*) AS cnt FROM {physical_table}", ())
        return count_row["cnt"] if count_row else 0
    except Exception as error:
        if logger is not None:
            from backend.services.support import write_application_exception_log

            write_application_exception_log(
                logger,
                logging.WARNING,
                "log_table_total_count_failed",
                error=error,
                table_id=table_id,
                data_table=physical_table,
            )
        return 0
