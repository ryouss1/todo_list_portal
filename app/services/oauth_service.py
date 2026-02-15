"""OAuth business logic."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app import config
from app.core.auth.audit import log_auth_event
from app.core.auth.oauth import OAuthUserInfo, get_provider_config
from app.core.auth.oauth.flow import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_userinfo,
    generate_code_challenge,
    generate_code_verifier,
    generate_state,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.crud import oauth_provider as crud_provider
from app.crud import oauth_state as crud_state
from app.crud import user as crud_user
from app.crud import user_oauth_account as crud_oauth_account
from app.models.oauth_provider import OAuthProvider
from app.models.user import User

logger = logging.getLogger("app.services.oauth")


def get_enabled_providers(db: Session) -> List[OAuthProvider]:
    """Get list of enabled OAuth providers (for login page)."""
    return crud_provider.get_enabled_providers(db)


def initiate_oauth(db: Session, provider_name: str, redirect_uri: str) -> str:
    """Start OAuth flow: generate state, store it, return authorize URL."""
    provider = crud_provider.get_provider_by_name(db, provider_name)
    if not provider or not provider.is_enabled:
        raise NotFoundError(f"OAuth provider '{provider_name}' not found or disabled")

    state = generate_state()
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.OAUTH_STATE_EXPIRY_SECONDS)
    crud_state.create_state(db, state, expires_at, code_verifier=code_verifier, redirect_uri=redirect_uri)
    db.commit()

    return build_authorize_url(provider, state, code_challenge, redirect_uri)


def handle_callback(
    db: Session,
    provider_name: str,
    code: str,
    state: str,
    redirect_uri: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    """Handle OAuth callback: validate state, exchange code, find/link user."""
    # 1. Validate state
    state_obj = crud_state.consume_state(db, state)
    if not state_obj:
        raise ConflictError("Invalid or expired OAuth state")

    # 2. Get provider
    provider = crud_provider.get_provider_by_name(db, provider_name)
    if not provider or not provider.is_enabled:
        raise NotFoundError(f"OAuth provider '{provider_name}' not found or disabled")

    # 3. Exchange code for token
    token_data = exchange_code_for_token(
        provider,
        code,
        state_obj.code_verifier or "",
        redirect_uri,
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise ConflictError("Failed to obtain access token")

    # 4. Fetch user info
    raw_userinfo = fetch_userinfo(provider, access_token)
    provider_config = get_provider_config(provider_name)
    if not provider_config:
        raise ConflictError(f"No config registered for provider '{provider_name}'")

    userinfo: OAuthUserInfo = provider_config.parse_userinfo(raw_userinfo)
    if not userinfo.provider_user_id:
        raise ConflictError("Could not get user ID from OAuth provider")

    # 5. Find existing link
    existing_link = crud_oauth_account.get_by_provider_user(
        db,
        provider.id,
        userinfo.provider_user_id,
    )
    if existing_link:
        user = crud_user.get_user(db, existing_link.user_id)
        if not user or not user.is_active:
            raise ConflictError("Linked account is disabled")
        # Update tokens
        existing_link.access_token = access_token
        existing_link.refresh_token = token_data.get("refresh_token")
        if "expires_in" in token_data:
            existing_link.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(token_data["expires_in"])
            )
        db.commit()
        log_auth_event(
            db,
            "oauth_login",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"provider": provider_name},
        )
        db.commit()
        return user

    # 6. Auto-link by email match
    if userinfo.email:
        user = crud_user.get_user_by_email(db, userinfo.email)
        if user:
            if not user.is_active:
                raise ConflictError("Account is disabled")
            _create_oauth_link(db, user.id, provider.id, userinfo, access_token, token_data)
            db.commit()
            log_auth_event(
                db,
                "oauth_link",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"provider": provider_name, "auto": True},
            )
            db.commit()
            return user

    # 7. No match — reject (no self-registration)
    raise ConflictError("No matching user found. Please ask an administrator to create your account first.")


def link_oauth_account(
    db: Session,
    user_id: int,
    provider_name: str,
    code: str,
    state: str,
    redirect_uri: str,
) -> None:
    """Link an OAuth account to an existing user."""
    state_obj = crud_state.consume_state(db, state)
    if not state_obj:
        raise ConflictError("Invalid or expired OAuth state")

    provider = crud_provider.get_provider_by_name(db, provider_name)
    if not provider or not provider.is_enabled:
        raise NotFoundError(f"OAuth provider '{provider_name}' not found or disabled")

    # Check if already linked
    existing = crud_oauth_account.get_by_user_and_provider(db, user_id, provider.id)
    if existing:
        raise ConflictError(f"Already linked to {provider_name}")

    token_data = exchange_code_for_token(
        provider,
        code,
        state_obj.code_verifier or "",
        redirect_uri,
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise ConflictError("Failed to obtain access token")

    raw_userinfo = fetch_userinfo(provider, access_token)
    provider_config = get_provider_config(provider_name)
    if not provider_config:
        raise ConflictError(f"No config registered for provider '{provider_name}'")

    userinfo = provider_config.parse_userinfo(raw_userinfo)

    # Check if this provider user is already linked to another user
    existing_other = crud_oauth_account.get_by_provider_user(
        db,
        provider.id,
        userinfo.provider_user_id,
    )
    if existing_other:
        raise ConflictError("This OAuth account is already linked to another user")

    _create_oauth_link(db, user_id, provider.id, userinfo, access_token, token_data)
    db.commit()
    log_auth_event(db, "oauth_link", user_id=user_id, details={"provider": provider_name})
    db.commit()


def unlink_oauth_account(db: Session, user_id: int, provider_name: str) -> None:
    """Unlink an OAuth account. Ensures at least one auth method remains."""
    provider = crud_provider.get_provider_by_name(db, provider_name)
    if not provider:
        raise NotFoundError(f"OAuth provider '{provider_name}' not found")

    link = crud_oauth_account.get_by_user_and_provider(db, user_id, provider.id)
    if not link:
        raise NotFoundError("OAuth account not linked")

    # Check if user has password — if not, must keep at least one OAuth link
    user = crud_user.get_user(db, user_id)
    if not user:
        raise NotFoundError("User not found")

    link_count = crud_oauth_account.count_by_user(db, user_id)
    if not user.password_hash and link_count <= 1:
        raise ConflictError("Cannot unlink last authentication method")

    crud_oauth_account.delete_account(db, link.id)
    db.commit()


def get_user_links(db: Session, user_id: int) -> list:
    """Get list of OAuth accounts linked to a user."""
    links = crud_oauth_account.get_by_user(db, user_id)
    result = []
    for link in links:
        provider = crud_provider.get_provider(db, link.provider_id)
        result.append(
            {
                "id": link.id,
                "provider_name": provider.name if provider else "unknown",
                "provider_display_name": provider.display_name if provider else "Unknown",
                "provider_email": link.provider_email,
                "created_at": link.created_at,
            }
        )
    return result


def _create_oauth_link(
    db: Session,
    user_id: int,
    provider_id: int,
    userinfo: OAuthUserInfo,
    access_token: str,
    token_data: dict,
) -> None:
    """Create a new OAuth account link."""
    data = {
        "user_id": user_id,
        "provider_id": provider_id,
        "provider_user_id": userinfo.provider_user_id,
        "provider_email": userinfo.email,
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
    }
    if "expires_in" in token_data:
        data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=int(token_data["expires_in"]))
    crud_oauth_account.create_account(db, data)
