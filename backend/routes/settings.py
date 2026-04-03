from __future__ import annotations

from fastapi import APIRouter, Request
import logging

from backend.schemas import *
from backend.services.support import *
from backend.services import support

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
    changed_section_keys = sorted(changes.keys())
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
        persist_connector_settings(connection, changes["connectors"])
        changes.pop("connectors", None)

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
        changed_sections=changed_section_keys,
        logging=settings_payload.get("logging"),
    )
    return AppSettingsResponse(**settings_payload)


@router.post("/api/v1/settings/data/backups", response_model=SettingsCreateBackupResponse)
def create_settings_backup(request: Request) -> SettingsCreateBackupResponse:
    logger = get_application_logger(request)
    try:
        result = support.create_backup()
        write_application_log(
            logger,
            logging.INFO,
            "settings_backup_created",
            filename=result.get("filename"),
            size_bytes=result.get("size_bytes"),
        )
        # Ensure required metadata fields exist for the response schema.
        backup_payload = {
            "id": result.get("id") or result.get("filename"),
            "filename": result.get("filename"),
            "created_at": result.get("created_at") or utc_now_iso(),
            "size_bytes": result.get("size_bytes"),
            "path": result.get("path"),
        }
        backup_meta = SettingsBackupMetadata(**backup_payload)
        return SettingsCreateBackupResponse(ok=True, message="Backup created", backup=backup_meta)
    except RuntimeError as exc:
        write_application_log(logger, logging.ERROR, "settings_backup_failed", error=str(exc))
        return SettingsCreateBackupResponse(ok=False, message=str(exc), backup=None)


@router.get("/api/v1/settings/data/backups", response_model=SettingsListBackupsResponse)
def list_settings_backups(request: Request) -> SettingsListBackupsResponse:
    directory = str(support.get_backup_dir())
    try:
        items = support.list_backups()
        normalized = []
        for i in items:
            normalized.append(
                {
                    "id": i.get("id") or i.get("filename"),
                    "filename": i.get("filename"),
                    "created_at": i.get("created_at") or utc_now_iso(),
                    "size_bytes": i.get("size_bytes"),
                    "path": i.get("path"),
                }
            )
        backups = [SettingsBackupMetadata(**i) for i in normalized]
        return SettingsListBackupsResponse(directory=directory, backups=backups)
    except RuntimeError as exc:
        logger = get_application_logger(request)
        write_application_log(logger, logging.ERROR, "settings_backup_list_failed", error=str(exc))
        return SettingsListBackupsResponse(directory=directory, backups=[])


@router.post("/api/v1/settings/data/backups/restore", response_model=SettingsBackupRestoreResponse)
def restore_settings_backup(payload: SettingsBackupRestoreRequest, request: Request) -> SettingsBackupRestoreResponse:
    logger = get_application_logger(request)
    try:
        res = support.restore_backup(payload.backup_id)
        write_application_log(logger, logging.INFO, "settings_backup_restored", filename=payload.backup_id)
        return SettingsBackupRestoreResponse(ok=True, message="Restore started", restored_at=res.get("restored_at"))
    except RuntimeError as exc:
        write_application_log(logger, logging.ERROR, "settings_backup_restore_failed", error=str(exc))
        return SettingsBackupRestoreResponse(ok=False, message=str(exc), restored_at=None)
