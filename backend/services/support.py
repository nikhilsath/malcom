from __future__ import annotations

import sqlite3
from typing import Any
from pathlib import Path

from fastapi import Request

from .api_serialization import *
from .automation_executor import *
from .connector_manager import *
from .helpers import *
from .scripts import *
from .settings import *
from .tool_integration import *
from . import helpers as _helpers


def get_connection(request: Request) -> sqlite3.Connection:
    return request.app.state.connection


def get_root_dir(request: Request) -> Path:
    return Path(request.app.state.root_dir)


def execute_automation_definition(*args: Any, **kwargs: Any):
    _helpers.execute_local_llm_chat_request = execute_local_llm_chat_request
    return _helpers.execute_automation_definition(*args, **kwargs)
