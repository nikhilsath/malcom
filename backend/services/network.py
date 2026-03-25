from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException, status

from backend.schemas import OutgoingAuthConfig, OutgoingApiTestRequest, OutgoingApiTestResponse, OutgoingWebhookSigningConfig


def header_subset(headers: Any) -> dict[str, str]:
    allowed_headers = {"content-type", "user-agent", "x-request-id"}
    return {
        key.lower(): value
        for key, value in headers.items()
        if key.lower() in allowed_headers
    }


def build_outgoing_request_headers(
    auth_type: str,
    auth_config: OutgoingAuthConfig | None,
    *,
    webhook_signing: OutgoingWebhookSigningConfig | None = None,
    request_body_bytes: bytes | None = None,
) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    config = auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and config.token:
        headers["Authorization"] = f"Bearer {config.token}"
    elif auth_type == "basic" and config.username and config.password:
        encoded = base64.b64encode(f"{config.username}:{config.password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"
    elif auth_type == "header" and config.header_name and config.header_value:
        headers[config.header_name] = config.header_value

    signing = webhook_signing or OutgoingWebhookSigningConfig()
    if signing.verification_token:
        headers["X-Malcom-Verification-Token"] = signing.verification_token

    if signing.algorithm == "hmac_sha256" and signing.signing_secret and signing.signature_header:
        digest = hmac.new(
            signing.signing_secret.encode("utf-8"),
            request_body_bytes or b"",
            hashlib.sha256,
        ).hexdigest()
        headers[signing.signature_header] = f"sha256={digest}"

    return headers


def redact_outgoing_request_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted_headers: dict[str, str] = {}

    for key, value in headers.items():
        if key.lower() == "authorization":
            if value.startswith("Bearer "):
                redacted_headers[key] = "Bearer [redacted]"
            elif value.startswith("Basic "):
                redacted_headers[key] = "Basic [redacted]"
            else:
                redacted_headers[key] = "[redacted]"
            continue

        redacted_headers[key] = "[redacted]" if key.lower() != "content-type" else value

    return redacted_headers


def execute_outgoing_test_delivery(payload: OutgoingApiTestRequest) -> OutgoingApiTestResponse:
    try:
        parsed_payload = json.loads(payload.payload_template)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    parsed_url = urllib.parse.urlparse(payload.destination_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    request_body = json.dumps(parsed_payload).encode("utf-8")
    headers = build_outgoing_request_headers(
        payload.auth_type,
        payload.auth_config,
        webhook_signing=payload.webhook_signing,
        request_body_bytes=request_body,
    )
    request = urllib.request.Request(
        payload.destination_url,
        data=request_body,
        headers=headers,
        method=payload.http_method,
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return OutgoingApiTestResponse(
                ok=200 <= response.status < 300,
                status_code=response.status,
                response_body=response_body[:2000],
                sent_headers=redact_outgoing_request_headers(headers),
                destination_url=payload.destination_url,
            )
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        return OutgoingApiTestResponse(
            ok=False,
            status_code=error.code,
            response_body=response_body[:2000],
            sent_headers=redact_outgoing_request_headers(headers),
            destination_url=payload.destination_url,
        )
    except urllib.error.URLError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to reach destination URL: {error.reason}.") from error
