from __future__ import annotations

import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import get_database_url
from backend.http_middleware import log_http_requests
from backend.routes.api import router as api_router
from backend.routes.ui import register_ui_routes, router as ui_router
from backend.schemas import LocalLlmChatResponse
from backend.services.support import (
    INBOUND_SECRET_BYTES,
    INBOUND_SECRET_PREFIX,
    execute_local_llm_chat_request,
    generate_secret,
    get_local_worker_id,
    get_project_root,
    get_ui_dir,
    get_ui_dist_dir,
    lifespan,
    send_smtp_relay_message,
)


def create_app() -> FastAPI:
    database_url = get_database_url()

    app = FastAPI(
        title="Malcom API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.db_path = "postgresql"
    app.state.database_url = database_url
    app.state.root_dir = get_project_root()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(log_http_requests)

    app.include_router(ui_router)
    app.include_router(api_router)
    register_ui_routes(app)

    project_root = get_project_root()
    app.mount("/assets", StaticFiles(directory=str(get_ui_dist_dir(project_root) / "assets"), check_dir=False), name="ui-assets")
    app.mount("/media", StaticFiles(directory=str(project_root / "media"), check_dir=False), name="media")
    app.mount("/scripts", StaticFiles(directory=str(get_ui_dir(project_root) / "scripts"), check_dir=False), name="ui-scripts")
    app.mount("/styles", StaticFiles(directory=str(get_ui_dir(project_root) / "styles"), check_dir=False), name="ui-styles")
    app.mount("/modals", StaticFiles(directory=str(get_ui_dir(project_root) / "modals"), check_dir=False), name="ui-modals")
    return app


app = create_app()
