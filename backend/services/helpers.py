"""Compatibility facade for historical ``backend.services.helpers`` imports."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from fastapi import Request

from . import api_resources as _api_resources
from . import app_lifecycle as _app_lifecycle
from . import automation_execution as _automation_execution
from . import automation_executor as _automation_executor
from . import connectors as _connectors
from . import logging_service as _logging_service
from . import network as _network
from . import runtime_dashboard as _runtime_dashboard
from . import runtime_workers as _runtime_workers
from . import serialization as _serialization
from . import tool_runtime as _tool_runtime
from . import ui_assets as _ui_assets
from . import utils as _utils

_automation_execute_definition = _automation_execution.execute_automation_definition
_automation_execute_local_llm_chat_request = _automation_execution.execute_local_llm_chat_request


def _bind_public(module: Any, names: Iterable[str]) -> None:
    for name in names:
        globals()[name] = getattr(module, name)


_bind_public(_utils, _utils.__all__)
_bind_public(_ui_assets, _ui_assets.__all__)
_bind_public(_serialization, _serialization.__all__)
_bind_public(_runtime_workers, _runtime_workers.__all__)
_bind_public(_connectors, _connectors.__all__)
_bind_public(_logging_service, _logging_service.__all__)
_bind_public(
    _network,
    [
        "build_outgoing_request_headers",
        "execute_outgoing_test_delivery",
        "header_subset",
        "redact_outgoing_request_headers",
    ],
)
_bind_public(_tool_runtime, _tool_runtime.__all__)
_bind_public(_runtime_dashboard, _runtime_dashboard.__all__)
_bind_public(_api_resources, _api_resources.__all__)
_bind_public(_app_lifecycle, _app_lifecycle.__all__)


def get_application_logger(request: Request) -> logging.Logger:
    logger = getattr(request.app.state, "logger", None)
    if logger is None:
        logger = configure_application_logger(
            request.app,
            root_dir=get_root_dir(request),
            max_file_size_mb=_automation_execution.DEFAULT_APP_SETTINGS["logging"]["max_file_size_mb"],
        )
        request.app.state.logger = logger
    return logger


def execute_outgoing_test_delivery(*args: Any, **kwargs: Any):
    return _network.execute_outgoing_test_delivery(*args, **kwargs)


def _execute_outgoing_test_delivery_proxy(*args: Any, **kwargs: Any):
    return execute_outgoing_test_delivery(*args, **kwargs)


def execute_connector_activity(*args: Any, **kwargs: Any):
    from .connector_activities import execute_connector_activity as _execute_connector_activity

    return _execute_connector_activity(*args, **kwargs)


def _execute_connector_activity_proxy(*args: Any, **kwargs: Any):
    return execute_connector_activity(*args, **kwargs)


def execute_local_llm_chat_request(*args: Any, **kwargs: Any):
    return _automation_execute_local_llm_chat_request(*args, **kwargs)


def _execute_local_llm_chat_request_proxy(*args: Any, **kwargs: Any):
    return execute_local_llm_chat_request(*args, **kwargs)


_automation_execution.execute_outgoing_test_delivery = _execute_outgoing_test_delivery_proxy
_automation_execution.execute_connector_activity = _execute_connector_activity_proxy
_automation_execution.execute_local_llm_chat_request = _execute_local_llm_chat_request_proxy
_automation_executor.execute_outgoing_test_delivery = _execute_outgoing_test_delivery_proxy
_automation_executor.execute_connector_activity = _execute_connector_activity_proxy
_automation_executor.execute_local_llm_chat_request = _execute_local_llm_chat_request_proxy


def execute_automation_definition(*args: Any, **kwargs: Any):
    _automation_execution.execute_local_llm_chat_request = _execute_local_llm_chat_request_proxy
    _automation_execution.execute_connector_activity = _execute_connector_activity_proxy
    _automation_execution.execute_outgoing_test_delivery = _execute_outgoing_test_delivery_proxy
    _automation_executor.execute_local_llm_chat_request = _execute_local_llm_chat_request_proxy
    _automation_executor.execute_connector_activity = _execute_connector_activity_proxy
    _automation_executor.execute_outgoing_test_delivery = _execute_outgoing_test_delivery_proxy
    return _automation_execute_definition(*args, **kwargs)


def __getattr__(name: str) -> Any:
    return getattr(_automation_execution, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | {name for name in dir(_automation_execution) if not name.startswith("_")})


__all__ = sorted(
    {
        name
        for name in dir(_automation_execution)
        if not name.startswith("_")
    }
    | {
        name
        for name in globals()
        if not name.startswith("_")
    }
)
