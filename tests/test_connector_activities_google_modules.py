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


def test_gmail_list_messages_schema_matches_documented_query_params() -> None:
    activity = next(definition for definition in GOOGLE_GMAIL_ACTIVITY_DEFINITIONS if definition.activity_id == "gmail_list_messages")

    assert [field["key"] for field in activity.input_schema] == [
        "q",
        "labels",
        "max_results",
        "page_token",
        "include_spam_trash",
    ]
    assert [field["label"] for field in activity.input_schema] == [
        "q",
        "labelIds[]",
        "maxResults",
        "pageToken",
        "includeSpamTrash",
    ]
    assert [field["key"] for field in activity.output_schema] == [
        "messages",
        "next_page_token",
        "result_size_estimate",
    ]


def test_gmail_get_message_and_thread_schema_include_metadata_headers() -> None:
    message_activity = next(definition for definition in GOOGLE_GMAIL_ACTIVITY_DEFINITIONS if definition.activity_id == "gmail_get_message")
    thread_activity = next(definition for definition in GOOGLE_GMAIL_ACTIVITY_DEFINITIONS if definition.activity_id == "gmail_get_thread")

    assert [field["key"] for field in message_activity.input_schema] == ["message_id", "format", "metadata_headers"]
    assert [field["key"] for field in thread_activity.input_schema] == ["thread_id", "format", "metadata_headers"]
    assert message_activity.input_schema[2]["label"] == "metadataHeaders[]"
    assert thread_activity.input_schema[2]["label"] == "metadataHeaders[]"


def test_drive_list_and_search_schema_include_pagination_and_shared_drive_controls() -> None:
    list_activity = next(definition for definition in GOOGLE_DRIVE_ACTIVITY_DEFINITIONS if definition.activity_id == "drive_list_files")
    search_activity = next(definition for definition in GOOGLE_DRIVE_ACTIVITY_DEFINITIONS if definition.activity_id == "drive_search_files")

    assert [field["key"] for field in list_activity.input_schema] == [
        "parent_id",
        "max_results",
        "page_token",
        "corpora",
        "drive_id",
        "include_items_from_all_drives",
        "order_by",
        "spaces",
        "supports_all_drives",
    ]
    assert [field["key"] for field in search_activity.input_schema] == [
        "search_query",
        "max_results",
        "page_token",
        "corpora",
        "drive_id",
        "include_items_from_all_drives",
        "order_by",
        "spaces",
        "supports_all_drives",
    ]
    assert "incomplete_search" in [field["key"] for field in list_activity.output_schema]
    assert "incomplete_search" in [field["key"] for field in search_activity.output_schema]


def test_calendar_and_sheets_schema_expose_documented_query_controls() -> None:
    calendar_activity = next(definition for definition in GOOGLE_CALENDAR_ACTIVITY_DEFINITIONS if definition.activity_id == "calendar_upcoming_events")
    read_range_activity = next(definition for definition in GOOGLE_SHEETS_ACTIVITY_DEFINITIONS if definition.activity_id == "sheets_read_range")
    update_range_activity = next(definition for definition in GOOGLE_SHEETS_ACTIVITY_DEFINITIONS if definition.activity_id == "sheets_update_range")
    append_rows_activity = next(definition for definition in GOOGLE_SHEETS_ACTIVITY_DEFINITIONS if definition.activity_id == "sheets_append_rows")

    assert [field["key"] for field in calendar_activity.input_schema] == [
        "calendar_id",
        "limit",
        "page_token",
        "search_query",
        "show_deleted",
        "time_max",
        "updated_min",
    ]
    assert [field["key"] for field in read_range_activity.input_schema] == [
        "spreadsheet_id",
        "range",
        "major_dimension",
        "value_render_option",
        "date_time_render_option",
    ]
    assert [field["key"] for field in update_range_activity.input_schema][-3:] == [
        "include_values_in_response",
        "response_value_render_option",
        "response_date_time_render_option",
    ]
    assert [field["key"] for field in append_rows_activity.input_schema][-3:] == [
        "include_values_in_response",
        "response_value_render_option",
        "response_date_time_render_option",
    ]
