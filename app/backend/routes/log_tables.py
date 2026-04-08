"""Backend routes for managing Log / Write-to-DB table definitions and their data."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.schemas import (
    LogDbRowsResponse,
    LogDbTableCreate,
    LogDbTableDetail,
    LogDbTableSummary,
)
from backend.services.support import (
    fetch_all,
    fetch_one,
    get_application_logger,
    get_connection,
    utc_now_iso,
)
from backend.services.log_table_schema import (
    assert_safe_identifier,
    create_log_table_ddl,
    data_table_name,
    get_log_table_row_or_404,
    persist_log_table_metadata,
)
from backend.services.log_table_queries import (
    build_column_response,
    build_table_summary,
    fetch_log_table_columns,
    fetch_log_table_rows,
    fetch_log_table_total,
)
from backend.services.log_table_import import insert_log_table_rows

router = APIRouter()


# ── List managed log tables ───────────────────────────────────────────────────

@router.get("/api/v1/log-tables", response_model=list[LogDbTableSummary])
def list_log_tables(request: Request) -> list[LogDbTableSummary]:
    connection = get_connection(request)
    rows = fetch_all(connection, "SELECT * FROM log_db_tables ORDER BY created_at DESC")
    return [build_table_summary(dict(row), connection) for row in rows]


# ── Create a new managed log table ───────────────────────────────────────────

@router.post("/api/v1/log-tables", response_model=LogDbTableDetail, status_code=status.HTTP_201_CREATED)
def create_log_table(payload: LogDbTableCreate, request: Request) -> LogDbTableDetail:
    connection = get_connection(request)
    assert_safe_identifier(payload.name)

    existing = fetch_one(connection, "SELECT id FROM log_db_tables WHERE name = ?", (payload.name,))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A log table named '{payload.name}' already exists.",
        )

    now = utc_now_iso()
    table_id = f"logtbl_{uuid4().hex[:10]}"
    physical_table = data_table_name(payload.name)

    create_log_table_ddl(connection, physical_table, payload.columns)
    col_responses = persist_log_table_metadata(
        connection,
        table_id=table_id,
        name=payload.name,
        description=payload.description,
        columns=payload.columns,
        now=now,
    )

    column_names = [c.column_name for c in payload.columns]
    imported_row_count = insert_log_table_rows(
        connection,
        physical_table=physical_table,
        column_names=column_names,
        rows=payload.rows,
    )

    connection.commit()

    return LogDbTableDetail(
        id=table_id,
        name=payload.name,
        description=payload.description,
        row_count=imported_row_count,
        created_at=now,
        updated_at=now,
        columns=col_responses,
    )


# ── Get a single managed log table ───────────────────────────────────────────

@router.get("/api/v1/log-tables/{table_id}", response_model=LogDbTableDetail)
def get_log_table(table_id: str, request: Request) -> LogDbTableDetail:
    connection = get_connection(request)
    row = get_log_table_row_or_404(connection, table_id)
    col_rows = fetch_all(
        connection,
        "SELECT * FROM log_db_columns WHERE table_id = ? ORDER BY position",
        (table_id,),
    )
    summary = build_table_summary(row, connection)
    return LogDbTableDetail(
        **summary.model_dump(),
        columns=[build_column_response(dict(c)) for c in col_rows],
    )


# ── Delete a managed log table ────────────────────────────────────────────────

@router.delete("/api/v1/log-tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log_table(table_id: str, request: Request) -> Response:
    connection = get_connection(request)
    row = get_log_table_row_or_404(connection, table_id)
    physical_table = data_table_name(row["name"])
    assert_safe_identifier(row["name"])
    connection.execute(f"DROP TABLE IF EXISTS {physical_table}")
    connection.execute("DELETE FROM log_db_tables WHERE id = ?", (table_id,))
    connection.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── List rows from a managed log table ───────────────────────────────────────

@router.get("/api/v1/log-tables/{table_id}/rows", response_model=LogDbRowsResponse)
def list_log_table_rows(table_id: str, request: Request, limit: int = 100) -> LogDbRowsResponse:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="limit must be between 1 and 1000.")
    connection = get_connection(request)
    row = get_log_table_row_or_404(connection, table_id)
    physical_table = data_table_name(row["name"])
    assert_safe_identifier(row["name"])
    logger = get_application_logger(request)

    col_names = fetch_log_table_columns(connection, table_id, physical_table=physical_table, logger=logger)
    data_rows = fetch_log_table_rows(connection, table_id=table_id, physical_table=physical_table, limit=limit, logger=logger)
    total = fetch_log_table_total(connection, table_id=table_id, physical_table=physical_table, logger=logger)

    return LogDbRowsResponse(
        table_id=table_id,
        table_name=row["name"],
        columns=col_names,
        rows=data_rows,
        total=total,
    )


# ── Clear all rows from a managed log table ───────────────────────────────────

@router.post("/api/v1/log-tables/{table_id}/rows/clear", status_code=status.HTTP_200_OK)
def clear_log_table_rows(table_id: str, request: Request) -> dict:
    connection = get_connection(request)
    row = get_log_table_row_or_404(connection, table_id)
    physical_table = data_table_name(row["name"])
    assert_safe_identifier(row["name"])
    connection.execute(f"DELETE FROM {physical_table}")
    connection.commit()
    return {"cleared": True, "table": row["name"]}

