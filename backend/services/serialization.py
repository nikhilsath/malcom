"""Row-to-response serializers for API, automation, and worker payloads.

Primary identifiers: ``row_to_*`` mappers, ``worker_to_response``, and
``claim_job_response`` used by route handlers and automation services.
"""

from __future__ import annotations

import json
from typing import Any

from backend.runtime import RegisteredWorker, RuntimeTriggerJob
from backend.schemas.apis import OutgoingApiDetailResponse, OutgoingAuthConfig, OutgoingWebhookSigningConfig
from backend.schemas.automation import AutomationStepConfig, AutomationStepDefinition
from backend.schemas.workers import WorkerClaimResponse, WorkerClaimedJobResponse, WorkerResponse

DatabaseRow = dict[str, Any]


def row_to_api_summary(row: DatabaseRow) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "path_slug": row["path_slug"],
        "auth_type": row["auth_type"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "endpoint_path": f"/api/v1/inbound/{row['id']}",
        "last_received_at": row["last_received_at"],
        "last_delivery_status": row["last_delivery_status"],
        "events_count": row["events_count"],
    }


def row_to_event(row: DatabaseRow) -> dict[str, Any]:
    payload_json = row["payload_json"]
    return {
        "event_id": row["event_id"],
        "api_id": row["api_id"],
        "received_at": row["received_at"],
        "status": row["status"],
        "request_headers_subset": json.loads(row["request_headers_subset"]),
        "payload_json": json.loads(payload_json) if payload_json else None,
        "source_ip": row["source_ip"],
        "error_message": row["error_message"],
    }


def row_to_run(row: DatabaseRow) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "automation_id": row["automation_id"],
        "trigger_type": row["trigger_type"],
        "status": row["status"],
        "worker_id": row["worker_id"] if "worker_id" in row.keys() else None,
        "worker_name": row["worker_name"] if "worker_name" in row.keys() else None,
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
        "error_summary": row["error_summary"],
    }


def row_to_run_step(row: DatabaseRow) -> dict[str, Any]:
    detail_json = row["detail_json"]
    response_body_json = row["response_body_json"] if "response_body_json" in row.keys() else None
    extracted_fields_json = row["extracted_fields_json"] if "extracted_fields_json" in row.keys() else None
    return {
        "step_id": row["step_id"],
        "run_id": row["run_id"],
        "step_name": row["step_name"],
        "status": row["status"],
        "request_summary": row["request_summary"],
        "response_summary": row["response_summary"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
        "detail_json": json.loads(detail_json) if detail_json else None,
        "response_body_json": json.loads(response_body_json) if response_body_json else None,
        "extracted_fields_json": json.loads(extracted_fields_json) if extracted_fields_json else None,
    }


def row_to_automation_summary(row: DatabaseRow) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "enabled": bool(row["enabled"]),
        "trigger_type": row["trigger_type"],
        "trigger_config": json.loads(row["trigger_config_json"]),
        "step_count": row["step_count"] if "step_count" in row.keys() else 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_run_at": row["last_run_at"] if "last_run_at" in row.keys() else None,
        "next_run_at": row["next_run_at"] if "next_run_at" in row.keys() else None,
    }


def row_to_automation_step(row: DatabaseRow) -> AutomationStepDefinition:
    row_keys = row.keys()
    return AutomationStepDefinition(
        id=row["step_id"],
        type=row["step_type"],
        name=row["name"],
        config=AutomationStepConfig(**json.loads(row["config_json"])),
        on_true_step_id=row["on_true_step_id"] if "on_true_step_id" in row_keys else None,
        on_false_step_id=row["on_false_step_id"] if "on_false_step_id" in row_keys else None,
        is_merge_target=bool(row["is_merge_target"]) if "is_merge_target" in row_keys else False,
    )


def worker_to_response(worker: RegisteredWorker) -> WorkerResponse:
    return WorkerResponse(
        worker_id=worker.worker_id,
        name=worker.name,
        hostname=worker.hostname,
        address=worker.address,
        capabilities=list(worker.capabilities),
        status=worker.status,
        created_at=worker.created_at,
        updated_at=worker.updated_at,
        last_seen_at=worker.last_seen_at,
    )


def claim_job_response(job: RuntimeTriggerJob) -> WorkerClaimResponse:
    return WorkerClaimResponse(
        job=WorkerClaimedJobResponse(
            job_id=job.job_id,
            run_id=job.run_id,
            step_id=job.step_id,
            worker_id=job.worker_id or "",
            worker_name=job.worker_name or "",
            trigger={
                "type": job.trigger.type,
                "api_id": job.trigger.api_id,
                "event_id": job.trigger.event_id,
                "payload": job.trigger.payload,
                "received_at": job.trigger.received_at,
            },
            claimed_at=job.claimed_at or "",
        )
    )


def row_to_simple_api_resource(row: DatabaseRow, *, api_type: str, endpoint_path: str | None = None) -> dict[str, Any]:
    webhook_signing_payload: dict[str, Any] = {}
    if "webhook_signing_json" in row.keys():
        try:
            webhook_signing_payload = json.loads(row["webhook_signing_json"] or "{}")
        except json.JSONDecodeError:
            webhook_signing_payload = {}

    return {
        "id": row["id"],
        "type": api_type,
        "name": row["name"],
        "description": row["description"],
        "path_slug": row["path_slug"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"] if "status" in row.keys() else None,
        "endpoint_path": endpoint_path,
        "destination_url": row["destination_url"] if "destination_url" in row.keys() else None,
        "http_method": row["http_method"] if "http_method" in row.keys() else None,
        "auth_type": row["auth_type"] if "auth_type" in row.keys() else None,
        "repeat_enabled": bool(row["repeat_enabled"]) if "repeat_enabled" in row.keys() else None,
        "repeat_interval_minutes": row["repeat_interval_minutes"] if "repeat_interval_minutes" in row.keys() else None,
        "payload_template": row["payload_template"] if "payload_template" in row.keys() else None,
        "webhook_signing": OutgoingWebhookSigningConfig(**webhook_signing_payload) if webhook_signing_payload else None,
        "scheduled_time": row["scheduled_time"] if "scheduled_time" in row.keys() else None,
        "schedule_expression": row["schedule_expression"] if "schedule_expression" in row.keys() else None,
        "stream_mode": row["stream_mode"] if "stream_mode" in row.keys() else None,
        "last_run_at": row["last_run_at"] if "last_run_at" in row.keys() else None,
        "next_run_at": row["next_run_at"] if "next_run_at" in row.keys() else None,
        "last_error": row["last_error"] if "last_error" in row.keys() else None,
        "callback_path": row["callback_path"] if "callback_path" in row.keys() else None,
        "signature_header": row["signature_header"] if "signature_header" in row.keys() else None,
        "event_filter": row["event_filter"] if "event_filter" in row.keys() else None,
        "has_verification_token": bool(row["verification_token"]) if "verification_token" in row.keys() else None,
        "has_signing_secret": bool(row["signing_secret"]) if "signing_secret" in row.keys() else None,
        "last_received_at": row["last_received_at"] if "last_received_at" in row.keys() else None,
        "last_delivery_status": row["last_delivery_status"] if "last_delivery_status" in row.keys() else None,
        "events_count": int(row["events_count"]) if "events_count" in row.keys() and row["events_count"] is not None else None,
    }


def row_to_outgoing_detail_response(
    row: DatabaseRow,
    *,
    api_type: str,
    endpoint_path: str,
    connection: Any | None = None,
) -> OutgoingApiDetailResponse:
    resource = row_to_simple_api_resource(row, api_type=api_type, endpoint_path=endpoint_path)
    auth_config_json = row["auth_config_json"] if "auth_config_json" in row.keys() else "{}"
    try:
        auth_config_payload = json.loads(auth_config_json or "{}")
    except json.JSONDecodeError:
        auth_config_payload = {}
    resource["auth_config"] = OutgoingAuthConfig(**auth_config_payload)
    if connection is not None:
        from .automation_execution import list_outgoing_delivery_history

        resource["recent_deliveries"] = list_outgoing_delivery_history(connection, resource_id=row["id"], resource_type=api_type)
    return OutgoingApiDetailResponse(**resource)


__all__ = [name for name in globals() if name.startswith("row_to_") or name in {"worker_to_response", "claim_job_response"}]
