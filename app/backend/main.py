from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import get_database_url
from backend.http_middleware import log_http_requests
from backend.routes.api import router as api_router
from backend.routes.ui import register_ui_routes, router as ui_router
from backend.services.platform_contracts import get_frontend_allowed_origins
from backend.services.support import (
    get_project_root,
    get_ui_dir,
    get_ui_dist_dir,
)
from backend.services.automation_execution import lifespan as automation_lifespan


def _env_var_enabled(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name, "").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"1", "true", "yes", "on"}


def create_app() -> FastAPI:
    database_url = get_database_url()
    cors_origins = get_frontend_allowed_origins()

    app = FastAPI(
        title="Malcom API",
        version="0.1.0",
        lifespan=automation_lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.db_path = "postgresql"
    app.state.database_url = database_url
    app.state.root_dir = get_project_root()
    app.state.skip_ui_build_check = os.getenv("MALCOM_SKIP_UI_BUILD_CHECK", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    app.state.backend_serves_ui = _env_var_enabled("MALCOM_BACKEND_SERVE_UI", default=True)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(log_http_requests)

    app.include_router(ui_router)
    app.include_router(api_router)
    if app.state.backend_serves_ui:
        register_ui_routes(app)

    project_root = get_project_root()
    if app.state.backend_serves_ui:
        app.mount("/assets", StaticFiles(directory=str(get_ui_dist_dir(project_root) / "assets"), check_dir=False), name="ui-assets")
        app.mount("/scripts", StaticFiles(directory=str(get_ui_dir(project_root) / "scripts"), check_dir=False), name="ui-scripts")
        app.mount("/styles", StaticFiles(directory=str(get_ui_dir(project_root) / "styles"), check_dir=False), name="ui-styles")
        app.mount("/modals", StaticFiles(directory=str(get_ui_dir(project_root) / "modals"), check_dir=False), name="ui-modals")
    app.mount("/media", StaticFiles(directory=str(project_root / "data" / "media"), check_dir=False), name="media")
    return app


app = create_app()
