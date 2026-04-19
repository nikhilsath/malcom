from __future__ import annotations

from fastapi import APIRouter, Request

from backend.schemas.platform import (
    FrontendAuthRefreshRequest,
    FrontendAuthRevokeRequest,
    FrontendAuthTokenCreateRequest,
    FrontendAuthTokenResponse,
    PlatformBootstrapResponse,
    PlatformEmbedDescriptor,
    PlatformPluginCatalogResponse,
)
from backend.services.platform_auth import create_frontend_session, refresh_frontend_session, require_platform_session, revoke_frontend_session
from backend.services.platform_contracts import build_platform_bootstrap, build_platform_embed_descriptor, build_platform_plugin_catalog

router = APIRouter()
PLATFORM_API_PREFIX = "/api/v1/platform"


@router.post(f"{PLATFORM_API_PREFIX}/auth/tokens", response_model=FrontendAuthTokenResponse)
def issue_frontend_auth_tokens(payload: FrontendAuthTokenCreateRequest, request: Request) -> FrontendAuthTokenResponse:
    session, access_token, refresh_token = create_frontend_session(
        request.app.state.connection,
        operator_name=payload.operator_name,
        bootstrap_token=payload.bootstrap_token,
        client_name=payload.client_name,
        requested_origin=payload.requested_origin,
        requested_scopes=payload.requested_scopes,
    )
    return FrontendAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=session.access_expires_at,
        refresh_expires_at=session.refresh_expires_at,
        session=session,
    )


@router.post(f"{PLATFORM_API_PREFIX}/auth/refresh", response_model=FrontendAuthTokenResponse)
def refresh_frontend_auth_tokens(payload: FrontendAuthRefreshRequest, request: Request) -> FrontendAuthTokenResponse:
    session, access_token, refresh_token = refresh_frontend_session(
        request.app.state.connection,
        refresh_token=payload.refresh_token,
        client_name=payload.client_name,
    )
    return FrontendAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=session.access_expires_at,
        refresh_expires_at=session.refresh_expires_at,
        session=session,
    )


@router.post(f"{PLATFORM_API_PREFIX}/auth/revoke", response_model=FrontendAuthTokenResponse)
def revoke_frontend_auth_tokens(payload: FrontendAuthRevokeRequest, request: Request) -> FrontendAuthTokenResponse:
    session = revoke_frontend_session(request.app.state.connection, refresh_token=payload.refresh_token)
    return FrontendAuthTokenResponse(
        access_token="",
        refresh_token="",
        access_expires_at=session.access_expires_at,
        refresh_expires_at=session.refresh_expires_at,
        session=session,
    )


@router.get(f"{PLATFORM_API_PREFIX}/bootstrap", response_model=PlatformBootstrapResponse)
def get_platform_bootstrap(request: Request) -> PlatformBootstrapResponse:
    session = require_platform_session(request)
    return build_platform_bootstrap(request, session=session)


@router.get(f"{PLATFORM_API_PREFIX}/plugins", response_model=PlatformPluginCatalogResponse)
def get_platform_plugins(request: Request) -> PlatformPluginCatalogResponse:
    require_platform_session(request)
    return build_platform_plugin_catalog()


@router.get(f"{PLATFORM_API_PREFIX}/embeds/{{embed_id}}", response_model=PlatformEmbedDescriptor)
def get_platform_embed_descriptor(embed_id: str, request: Request) -> PlatformEmbedDescriptor:
    require_platform_session(request)
    return build_platform_embed_descriptor(request, embed_id=embed_id)
