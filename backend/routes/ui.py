from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse

from backend.services.support import ensure_built_ui, get_built_ui_file, get_root_dir

router = APIRouter(include_in_schema=False)

UI_HTML_ROUTES = {
    "/settings/workspace.html": "settings/workspace.html",
    "/settings/logging.html": "settings/logging.html",
    "/settings/notifications.html": "settings/notifications.html",
    "/settings/access.html": "settings/access.html",
    "/settings/connectors.html": "settings/connectors.html",
    "/settings/data.html": "settings/data.html",
    "/automations/overview.html": "automations/overview.html",
    "/apis/registry.html": "apis/registry.html",
    "/apis/incoming.html": "apis/incoming.html",
    "/apis/outgoing.html": "apis/outgoing.html",
    "/apis/webhooks.html": "apis/webhooks.html",
    "/apis/automation.html": "apis/automation.html",
    "/tools/catalog.html": "tools/catalog.html",
    "/tools/coqui-tts.html": "tools/coqui-tts.html",
    "/tools/convert-audio.html": "tools/convert-audio.html",
    "/tools/convert-video.html": "tools/convert-video.html",
    "/tools/grafana.html": "tools/grafana.html",
    "/tools/llm-deepl.html": "tools/llm-deepl.html",
    "/tools/ocr-transcribe.html": "tools/ocr-transcribe.html",
    "/tools/smtp.html": "tools/smtp.html",
    "/tools/sftp.html": "tools/sftp.html",
    "/tools/storage.html": "tools/storage.html",
    "/scripts.html": "scripts.html",
    "/scripts/library.html": "scripts/library.html",
    "/dashboard/home.html": "dashboard/home.html",
}


def get_ui_html_response(relative_path: str, request: Request) -> FileResponse:
    root_dir = get_root_dir(request)
    ensure_built_ui(root_dir)
    html_path = get_built_ui_file(root_dir, relative_path)
    if not html_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UI page not found.")
    return FileResponse(html_path)


def build_ui_route(relative_path: str):
    def serve_ui_route(request: Request) -> FileResponse:
        return get_ui_html_response(relative_path, request)

    return serve_ui_route


def register_ui_routes(app: FastAPI) -> None:
    for route_path, relative_path in UI_HTML_ROUTES.items():
        app.add_api_route(
            route_path,
            build_ui_route(relative_path),
            methods=["GET"],
            include_in_schema=False,
        )


@router.get("/")
@router.get("/index.html")
def redirect_index_root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/home.html")


@router.get("/dashboard")
@router.get("/dashboard/")
def redirect_dashboard_root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/home.html")


@router.get("/settings")
@router.get("/settings/")
def redirect_settings_root() -> RedirectResponse:
    return RedirectResponse(url="/settings/workspace.html")


@router.get("/settings.html")
@router.get("/settings/general.html")
def redirect_settings_legacy_general() -> RedirectResponse:
    return RedirectResponse(url="/settings/workspace.html")


@router.get("/settings/security.html")
def redirect_settings_legacy_security() -> RedirectResponse:
    return RedirectResponse(url="/settings/access.html")


@router.get("/dashboard/overview.html")
def redirect_dashboard_overview() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/home.html")


@router.get("/dashboard/devices.html")
def redirect_dashboard_devices() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/home.html#/devices")


@router.get("/dashboard/logs.html")
def redirect_dashboard_logs() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/home.html#/logs")


@router.get("/automations")
@router.get("/automations/")
def redirect_automations_root() -> RedirectResponse:
    return RedirectResponse(url="/automations/overview.html")


@router.get("/apis")
@router.get("/apis/")
def redirect_apis_root() -> RedirectResponse:
    return RedirectResponse(url="/apis/registry.html")


@router.get("/apis.html")
@router.get("/apis/overview.html")
def redirect_apis_legacy_root() -> RedirectResponse:
    return RedirectResponse(url="/apis/registry.html")


@router.get("/tools")
@router.get("/tools/")
def redirect_tools_root() -> RedirectResponse:
    return RedirectResponse(url="/tools/catalog.html")


@router.get("/tools.html")
@router.get("/tools/overview.html")
def redirect_tools_legacy_root() -> RedirectResponse:
    return RedirectResponse(url="/tools/catalog.html")


@router.get("/scripts")
@router.get("/scripts/")
def redirect_scripts_root() -> RedirectResponse:
    return RedirectResponse(url="/scripts.html")
