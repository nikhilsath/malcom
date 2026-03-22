from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


@router.post("/api/v1/scripts/validate", response_model=ScriptValidationResult)
def validate_script(request_payload: ScriptValidationRequest, request: Request) -> ScriptValidationResult:
    return validate_script_payload(
        request_payload.language,
        request_payload.code,
        root_dir=get_root_dir(request),
    )


@router.get("/api/v1/scripts", response_model=list[ScriptSummaryResponse])
def list_scripts(request: Request) -> list[ScriptSummaryResponse]:
    rows = fetch_all(
        get_connection(request),
        """
        SELECT id, name, description, language, sample_input, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        ORDER BY updated_at DESC, lower(name) ASC
        """,
    )
    return [row_to_script_summary(row) for row in rows]


@router.get("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def get_script(script_id: str, request: Request) -> ScriptResponse:
    row = fetch_one(
        get_connection(request),
        """
        SELECT id, name, description, language, sample_input, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    return row_to_script_response(row)


@router.post("/api/v1/scripts", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(payload: ScriptCreate, request: Request) -> ScriptResponse:
    validation_result = validate_script_payload(payload.language, payload.code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    now = utc_now_iso()
    script_id = f"script_{uuid4().hex[:12]}"
    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    connection = get_connection(request)
    connection.execute(
        """
        INSERT INTO scripts (
            id, name, description, language, sample_input, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            script_id,
            payload.name.strip(),
            payload.description.strip(),
            payload.language,
            payload.sample_input,
            payload.code,
            validation_status,
            validation_message,
            last_validated_at,
            now,
            now,
        ),
    )
    connection.commit()
    row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, sample_input, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(row)


@router.patch("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def update_script(script_id: str, payload: ScriptUpdate, request: Request) -> ScriptResponse:
    connection = get_connection(request)
    existing_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, sample_input, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if existing_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row_to_script_response(existing_row)

    next_name = (changes.get("name") if "name" in changes else existing_row["name"]).strip()
    next_description = (changes.get("description") if "description" in changes else existing_row["description"]).strip()
    next_language = changes.get("language", existing_row["language"])
    next_sample_input = changes.get("sample_input", existing_row["sample_input"])
    next_code = changes.get("code", existing_row["code"])

    validation_result = validate_script_payload(next_language, next_code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    updated_at = utc_now_iso()
    connection.execute(
        """
        UPDATE scripts
        SET name = ?, description = ?, language = ?, sample_input = ?, code = ?, validation_status = ?, validation_message = ?, last_validated_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            next_name,
            next_description,
            next_language,
            next_sample_input,
            next_code,
            validation_status,
            validation_message,
            last_validated_at,
            updated_at,
            script_id,
        ),
    )
    connection.commit()
    saved_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, sample_input, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(saved_row)
