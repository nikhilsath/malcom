from __future__ import annotations

from backend.services.connector_activities_google import GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS, GOOGLE_HANDLER_REGISTRY
from backend.services.connector_activities_google_calendar import GOOGLE_CALENDAR_ACTIVITY_DEFINITIONS, GOOGLE_CALENDAR_HANDLER_REGISTRY
from backend.services.connector_activities_google_drive import GOOGLE_DRIVE_ACTIVITY_DEFINITIONS, GOOGLE_DRIVE_HANDLER_REGISTRY
from backend.services.connector_activities_google_gmail import GOOGLE_GMAIL_ACTIVITY_DEFINITIONS, GOOGLE_GMAIL_HANDLER_REGISTRY
from backend.services.connector_activities_google_sheets import GOOGLE_SHEETS_ACTIVITY_DEFINITIONS, GOOGLE_SHEETS_HANDLER_REGISTRY


def test_google_activity_barrel_includes_all_service_definitions() -> None:
    expected_activity_ids = {
        definition.activity_id
        for definition in (
            *GOOGLE_GMAIL_ACTIVITY_DEFINITIONS,
            *GOOGLE_DRIVE_ACTIVITY_DEFINITIONS,
            *GOOGLE_CALENDAR_ACTIVITY_DEFINITIONS,
            *GOOGLE_SHEETS_ACTIVITY_DEFINITIONS,
        )
    }

    assert {definition.activity_id for definition in GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS} == expected_activity_ids


def test_google_activity_barrel_includes_all_service_handlers() -> None:
    expected_kinds = (
        set(GOOGLE_GMAIL_HANDLER_REGISTRY)
        | set(GOOGLE_DRIVE_HANDLER_REGISTRY)
        | set(GOOGLE_CALENDAR_HANDLER_REGISTRY)
        | set(GOOGLE_SHEETS_HANDLER_REGISTRY)
    )

    assert set(GOOGLE_HANDLER_REGISTRY) == expected_kinds


def test_google_drive_registry_uses_named_functions() -> None:
    assert GOOGLE_HANDLER_REGISTRY["google_drive_list_files"].__name__ == "google_drive_list_files"
    assert GOOGLE_HANDLER_REGISTRY["google_drive_search_files"].__name__ == "google_drive_search_files"
    assert GOOGLE_HANDLER_REGISTRY["google_drive_upload_file"].__name__ == "google_drive_upload_file"
    assert GOOGLE_HANDLER_REGISTRY["google_drive_create_file"].__name__ == "google_drive_create_file"
