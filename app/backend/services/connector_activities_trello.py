from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


TRELLO_CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="trello",
        activity_id="trello_list_board_cards",
        service="boards",
        operation_type="read",
        label="List board cards",
        description="List cards from a Trello board and return normalized card summaries.",
        required_scopes=(),
        input_schema=(
            _field("board_id", "Board ID", "string", required=True),
            _field("limit", "Limit", "integer", required=False, default=20),
            _field("card_filter", "Card filter", "string", required=False, default="all"),
            _field("fields", "Fields", "string", required=False, default="id,name,idList,url,closed,due"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("board_id", "Board ID", "string"),
            _output("cards", "Cards", "array"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "trello_list_board_cards"},
    ),
    ConnectorActivityDefinition(
        provider_id="trello",
        activity_id="trello_create_card",
        service="cards",
        operation_type="write",
        label="Create card",
        description="Create a Trello card on a list and return the new card metadata.",
        required_scopes=(),
        input_schema=(
            _field("list_id", "List ID", "string", required=True),
            _field("name", "Name", "string", required=True),
            _field("desc", "Description", "textarea", required=False),
            _field("due", "Due", "string", required=False),
            _field("pos", "Position", "string", required=False, default="top"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("card_id", "Card ID", "string"),
            _output("url", "URL", "string"),
            _output("card", "Card", "object"),
        ),
        execution={"kind": "trello_create_card"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _normalize_trello_card(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "id_list": item.get("idList"),
        "url": item.get("url"),
        "closed": bool(item.get("closed")),
        "due": item.get("due"),
    }


def trello_list_board_cards(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    board_id = str(resolved_inputs.get("board_id") or "")
    params = {
        "limit": max(1, min(_coerce_int(resolved_inputs.get("limit"), 20), 1000)),
        "filter": str(resolved_inputs.get("card_filter") or "all"),
        "fields": str(resolved_inputs.get("fields") or "id,name,idList,url,closed,due"),
    }
    query = urllib.parse.urlencode(params)
    status_code, payload = _execute_request(executor, f"{base_url}/boards/{board_id}/cards?{query}", "GET", headers)
    _raise_for_status(status_code)
    cards = [_normalize_trello_card(item) for item in (payload or [])]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "board_id": board_id,
        "cards": cards,
        "count": len(cards),
    }


def trello_create_card(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    body = {
        "idList": str(resolved_inputs.get("list_id") or ""),
        "name": str(resolved_inputs.get("name") or ""),
        "desc": str(resolved_inputs.get("desc") or ""),
        "due": str(resolved_inputs.get("due") or ""),
        "pos": str(resolved_inputs.get("pos") or "top"),
    }
    status_code, payload = _execute_request(executor, f"{base_url}/cards", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    card = _normalize_trello_card(payload)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "card_id": card.get("id"),
        "url": card.get("url"),
        "card": card,
    }


TRELLO_HANDLER_REGISTRY = {
    "trello_list_board_cards": trello_list_board_cards,
    "trello_create_card": trello_create_card,
}
