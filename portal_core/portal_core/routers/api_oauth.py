"""OAuth API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from portal_core import config
from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.crud import oauth_provider as crud_provider
from portal_core.database import get_db
from portal_core.schemas.oauth import (
    OAuthLinkResponse,
    OAuthProviderCreate,
    OAuthProviderPublic,
    OAuthProviderResponse,
    OAuthProviderUpdate,
)
from portal_core.services import oauth_service

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])
admin_router = APIRouter(prefix="/api/admin/oauth-providers", tags=["oauth-admin"])


# ---------------------------------------------------------------------------
# Public OAuth endpoints (no auth required)
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=List[OAuthProviderPublic])
def list_providers(db: Session = Depends(get_db)):
    """Get enabled OAuth providers (for login page)."""
    return oauth_service.get_enabled_providers(db)


@router.get("/{provider}/authorize")
def authorize(provider: str, request: Request, db: Session = Depends(get_db)):
    """Initiate OAuth flow — redirects to provider."""
    redirect_uri = f"{config.OAUTH_CALLBACK_BASE_URL}/api/auth/oauth/{provider}/callback"
    url = oauth_service.initiate_oauth(db, provider, redirect_uri)
    return RedirectResponse(url=url)


@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth callback — logs in or links user."""
    redirect_uri = f"{config.OAUTH_CALLBACK_BASE_URL}/api/auth/oauth/{provider}/callback"
    ip_address = ""
    user_agent = ""
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        ip_address = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")
        user_agent = request.headers.get("user-agent", "")

    user = oauth_service.handle_callback(
        db,
        provider,
        code,
        state,
        redirect_uri,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    # Set session
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["display_name"] = user.display_name
    request.session["session_version"] = user.session_version
    return RedirectResponse(url="/", status_code=302)


# ---------------------------------------------------------------------------
# Authenticated user endpoints
# ---------------------------------------------------------------------------


@router.post("/{provider}/link")
def link_account(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Link an OAuth account to the current user."""
    redirect_uri = f"{config.OAUTH_CALLBACK_BASE_URL}/api/auth/oauth/{provider}/callback"
    oauth_service.link_oauth_account(db, user_id, provider, code, state, redirect_uri)
    return {"detail": f"Linked {provider} account"}


@router.delete("/{provider}/unlink")
def unlink_account(
    provider: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Unlink an OAuth account from the current user."""
    oauth_service.unlink_oauth_account(db, user_id, provider)
    return {"detail": f"Unlinked {provider} account"}


@router.get("/my-links", response_model=List[OAuthLinkResponse])
def my_links(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get OAuth accounts linked to the current user."""
    return oauth_service.get_user_links(db, user_id)


# ---------------------------------------------------------------------------
# Admin provider management
# ---------------------------------------------------------------------------


@admin_router.get("/", response_model=List[OAuthProviderResponse])
def list_all_providers(db: Session = Depends(get_db), _admin: int = Depends(require_admin)):
    return crud_provider.get_providers(db)


@admin_router.post("/", response_model=OAuthProviderResponse, status_code=201)
def create_provider(
    data: OAuthProviderCreate,
    db: Session = Depends(get_db),
    _admin: int = Depends(require_admin),
):
    return crud_provider.create_provider(db, data.model_dump())


@admin_router.put("/{provider_id}", response_model=OAuthProviderResponse)
def update_provider(
    provider_id: int,
    data: OAuthProviderUpdate,
    db: Session = Depends(get_db),
    _admin: int = Depends(require_admin),
):
    from portal_core.core.exceptions import NotFoundError

    update_data = data.model_dump(exclude_unset=True)
    result = crud_provider.update_provider(db, provider_id, update_data)
    if not result:
        raise NotFoundError("OAuth provider not found")
    return result


@admin_router.delete("/{provider_id}", status_code=204)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: int = Depends(require_admin),
):
    from portal_core.core.exceptions import NotFoundError

    if not crud_provider.delete_provider(db, provider_id):
        raise NotFoundError("OAuth provider not found")
