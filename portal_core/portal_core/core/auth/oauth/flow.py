"""OAuth Authorization Code + PKCE flow utilities."""

import asyncio
import base64
import hashlib
import logging
import secrets
from typing import Optional

import httpx
from httpx_oauth.oauth2 import BaseOAuth2

from portal_core.models.oauth_provider import OAuthProvider

logger = logging.getLogger("app.core.auth.oauth.flow")


# --- PKCE helpers (unchanged) ---


def generate_state() -> str:
    """Generate a cryptographically secure random state parameter."""
    return secrets.token_urlsafe(48)


def generate_code_verifier() -> str:
    """Generate a PKCE code_verifier."""
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    """Generate a PKCE code_challenge from a code_verifier (S256)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# --- httpx-oauth client factory ---


def _make_client(provider: OAuthProvider) -> BaseOAuth2:
    """Instantiate a BaseOAuth2 client from DB provider config."""
    return BaseOAuth2(
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        authorize_endpoint=provider.authorize_url,
        access_token_endpoint=provider.token_url,
        name=provider.name,
        base_scopes=provider.scopes.split() if provider.scopes else [],
    )


# --- Public sync functions (unchanged signatures) ---


def build_authorize_url(
    provider: OAuthProvider,
    state: str,
    code_challenge: str,
    redirect_uri: str,
) -> str:
    """Build the OAuth authorization URL with PKCE S256 challenge."""

    async def _build() -> str:
        return await _make_client(provider).get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

    return asyncio.run(_build())


def exchange_code_for_token(
    provider: OAuthProvider,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """Exchange an authorization code for access/refresh tokens."""

    async def _exchange() -> dict:
        token = await _make_client(provider).get_access_token(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
        return dict(token)  # OAuth2Token → dict for backward compat

    return asyncio.run(_exchange())


def fetch_userinfo(
    provider: OAuthProvider,
    access_token: str,
    extra_headers: Optional[dict] = None,
) -> dict:
    """Fetch user info from the provider's userinfo endpoint."""

    async def _fetch() -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(provider.userinfo_url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    return asyncio.run(_fetch())
