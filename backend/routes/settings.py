from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


@router.get("/api/v1/settings", response_model=AppSettingsResponse)
def get_app_settings(request: Request) -> AppSettingsResponse:
    payload = get_settings_payload(
        get_connection(request),
        protection_secret=get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path),
    )
    return AppSettingsResponse(**payload)


@router.patch("/api/v1/settings", response_model=AppSettingsResponse)
def patch_app_settings(payload: AppSettingsUpdate, request: Request) -> AppSettingsResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    changes = payload.model_dump(exclude_unset=True)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)

    if not changes:
        return AppSettingsResponse(**get_settings_payload(connection, protection_secret=protection_secret))

    if "connectors" in changes:
        changes["connectors"] = normalize_connector_settings_for_storage(
            changes["connectors"],
            existing_settings=get_stored_connector_settings(connection),
            connection=connection,
            protection_secret=protection_secret,
        )

    now = utc_now_iso()

    for key, value in changes.items():
        connection.execute(
            """
            INSERT INTO settings (key, value_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """
            ,
            (key, json.dumps(value), now, now),
        )

    connection.commit()
    settings_payload = get_settings_payload(connection, protection_secret=protection_secret)
    if "logging" in changes:
        request.app.state.logger = configure_application_logger(
            request.app,
            root_dir=get_root_dir(request),
            max_file_size_mb=settings_payload["logging"]["max_file_size_mb"],
        )
        logger = request.app.state.logger
    write_application_log(
        logger,
        logging.INFO,
        "settings_updated",
        changed_sections=sorted(changes.keys()),
        logging=settings_payload.get("logging"),
    )
    return AppSettingsResponse(**settings_payload)
