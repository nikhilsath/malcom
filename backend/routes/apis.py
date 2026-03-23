from __future__ import annotations

from fastapi import APIRouter

from backend.database import is_unique_violation
from backend.schemas import *
from backend.services.apis import (
    create_api_resource_record,
    create_inbound_api_record,
    receive_inbound_api_event,
    update_inbound_api_record,
    update_outgoing_api_record,
)
from backend.services.support import *

router = APIRouter()


@router.get("/api/v1/inbound", response_model=list[InboundApiResponse])
def list_inbound_apis(request: Request) -> list[InboundApiResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        WITH filtered_events AS (
            SELECT api_id, event_id, received_at, status
            FROM inbound_api_events
            WHERE is_mock = 0
        ),
        event_aggregates AS (
            SELECT
                api_id,
                COUNT(event_id) AS events_count,
                MAX(received_at) AS last_received_at
            FROM filtered_events
            GROUP BY api_id
        ),
        ranked_events AS (
            SELECT
                api_id,
                status,
                ROW_NUMBER() OVER (PARTITION BY api_id ORDER BY received_at DESC) AS row_number
            FROM filtered_events
        )
        SELECT
            inbound_apis.*,
            COALESCE(event_aggregates.events_count, 0) AS events_count,
            event_aggregates.last_received_at,
            ranked_events.status AS last_delivery_status
        FROM inbound_apis
        LEFT JOIN event_aggregates ON event_aggregates.api_id = inbound_apis.id
        LEFT JOIN ranked_events ON ranked_events.api_id = inbound_apis.id AND ranked_events.row_number = 1
        WHERE inbound_apis.is_mock = 0
        ORDER BY inbound_apis.created_at DESC
        """,
    )
    return [InboundApiResponse(**row_to_api_summary(row)) for row in rows]


@router.post("/api/v1/inbound", response_model=InboundApiCreated, status_code=status.HTTP_201_CREATED)
def create_inbound_api(payload: InboundApiCreate, request: Request) -> InboundApiCreated:
    return create_inbound_api_record(
        get_connection(request),
        payload=payload,
        base_url=str(request.base_url).rstrip("/"),
        logger=get_application_logger(request),
    )


@router.get("/api/v1/outgoing/scheduled", response_model=list[ApiResourceResponse])
def list_outgoing_scheduled_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, destination_url, http_method, auth_type,
               payload_template, scheduled_time, schedule_expression, status, created_at, updated_at
        FROM outgoing_scheduled_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_scheduled", endpoint_path="/api/v1/outgoing/scheduled"))
        for row in rows
    ]


@router.get("/api/v1/outgoing/continuous", response_model=list[ApiResourceResponse])
def list_outgoing_continuous_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, repeat_interval_minutes, destination_url, http_method, auth_type,
               payload_template, stream_mode, created_at, updated_at
        FROM outgoing_continuous_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_continuous", endpoint_path="/api/v1/outgoing/continuous"))
        for row in rows
    ]


@router.get("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def get_outgoing_api_detail(
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
    request: Request,
) -> OutgoingApiDetailResponse:
    connection = get_connection(request)
    row = get_outgoing_api_or_404(connection, api_id, api_type)
    endpoint_path = "/api/v1/outgoing/scheduled" if api_type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    return row_to_outgoing_detail_response(row, api_type=api_type, endpoint_path=endpoint_path)


@router.get("/api/v1/webhooks", response_model=list[ApiResourceResponse])
def list_webhook_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, callback_path, signature_header, event_filter, verification_token, signing_secret, created_at, updated_at
        FROM webhook_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="webhook", endpoint_path="/api/v1/webhooks"))
        for row in rows
    ]


@router.post("/api/v1/apis", response_model=ApiResourceResponse, status_code=status.HTTP_201_CREATED)
def create_api_resource(payload: ApiResourceCreate, request: Request) -> ApiResourceResponse:
    return create_api_resource_record(
        get_connection(request),
        payload=payload,
        base_url=str(request.base_url).rstrip("/"),
        root_dir=get_root_dir(request),
        db_path=request.app.state.db_path,
    )


@router.post("/api/v1/apis/test-delivery", response_model=OutgoingApiTestResponse)
def test_outgoing_api_delivery(payload: OutgoingApiTestRequest, request: Request) -> OutgoingApiTestResponse:
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        get_connection(request),
        connector_id=payload.connector_id,
        destination_url=payload.destination_url,
        auth_type=payload.auth_type,
        auth_config=payload.auth_config,
        protection_secret=get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path),
    )
    return execute_outgoing_test_delivery(
        OutgoingApiTestRequest(
            **payload.model_dump(exclude={"destination_url", "auth_type", "auth_config"}),
            destination_url=destination_url,
            auth_type=auth_type,
            auth_config=auth_config,
        )
    )


@router.get("/api/v1/inbound/{api_id}", response_model=InboundApiDetail)
def get_inbound_api(api_id: str, request: Request) -> InboundApiDetail:
    connection = get_connection(request)
    return serialize_api_detail(connection, api_id, request)


@router.patch("/api/v1/inbound/{api_id}", response_model=InboundApiResponse)
def update_inbound_api(api_id: str, payload: InboundApiUpdate, request: Request) -> InboundApiResponse:
    return update_inbound_api_record(
        get_connection(request),
        api_id=api_id,
        payload=payload,
        logger=get_application_logger(request),
    )


@router.patch("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def update_outgoing_api(api_id: str, payload: OutgoingApiUpdate, request: Request) -> OutgoingApiDetailResponse:
    return update_outgoing_api_record(
        get_connection(request),
        api_id=api_id,
        payload=payload,
        logger=get_application_logger(request),
    )


@router.post("/api/v1/inbound/{api_id}/rotate-secret", response_model=InboundSecretResponse)
def rotate_inbound_api_secret(api_id: str, request: Request) -> InboundSecretResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    api_row = get_api_or_404(connection, api_id)
    secret = generate_secret()
    connection.execute(
        "UPDATE inbound_apis SET secret_hash = ?, updated_at = ? WHERE id = ?",
        (hash_secret(secret), utc_now_iso(), api_row["id"]),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_secret_rotated",
        api_id=api_id,
    )
    return InboundSecretResponse(
        id=api_id,
        secret=secret,
        endpoint_url=str(request.base_url).rstrip("/") + f"/api/v1/inbound/{api_id}",
    )


@router.post("/api/v1/inbound/{api_id}/disable", response_model=InboundApiResponse)
def disable_inbound_api(api_id: str, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    get_api_or_404(connection, api_id)
    connection.execute(
        "UPDATE inbound_apis SET enabled = 0, updated_at = ? WHERE id = ?",
        (utc_now_iso(), api_id),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_disabled",
        api_id=api_id,
    )
    return InboundApiResponse(**row_to_api_summary(get_api_or_404(connection, api_id)))


@router.post("/api/v1/inbound/{api_id}", response_model=InboundReceiveAccepted, status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound_event(api_id: str, request: Request, response: Response) -> InboundReceiveAccepted:
    result = await receive_inbound_api_event(
        get_connection(request),
        api_id=api_id,
        request=request,
        logger=get_application_logger(request),
        root_dir=get_root_dir(request),
        database_url=request.app.state.database_url,
    )
    response.headers["X-Malcom-Event-Id"] = result.event_id
    return result.accepted
