from __future__ import annotations

from typing import Any
from pathlib import Path

from fastapi import Request

from .api_serialization import *
from .automation_executor import *
from .connectors import *
from .connector_activities import *
from .helpers import *
from .network import *
from .scripts import *
from .settings import *
from .settings_backup_restore import create_backup, get_backup_dir, list_backups, restore_backup
from .tool_integration import *
from .workflow_builder import *
from .utils import *
from .validation import *
from . import helpers as _helpers
from backend.routes.connectors import _provider_display_name, _provider_metadata, _resolve_token_expiry


def get_connection(request: Request) -> Any:
    return request.app.state.connection


def get_root_dir(request: Request) -> Path:
    return Path(request.app.state.root_dir)


def execute_automation_definition(*args: Any, **kwargs: Any):
    _helpers.execute_local_llm_chat_request = execute_local_llm_chat_request
    return _helpers.execute_automation_definition(*args, **kwargs)
