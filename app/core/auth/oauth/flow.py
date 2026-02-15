"""OAuth Authorization Code + PKCE flow utilities."""

import base64
import hashlib
import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.models.oauth_provider import OAuthProvider

logger = logging.getLogger("app.core.auth.oauth.flow")


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


def build_authorize_url(
    provider: OAuthProvider,
    state: str,
    code_challenge: str,
    redirect_uri: str,
) -> str:
    """Build the OAuth authorization URL."""
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": provider.scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{provider.authorize_url}?{urlencode(params)}"


def exchange_code_for_token(
    provider: OAuthProvider,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """Exchange an authorization code for access/refresh tokens."""
    data = {
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            provider.token_url,
            data=data,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def fetch_userinfo(
    provider: OAuthProvider,
    access_token: str,
    extra_headers: Optional[dict] = None,
) -> dict:
    """Fetch user info from the provider's userinfo endpoint."""
    headers = {"Authorization": f"Bearer {access_token}"}
    if extra_headers:
        headers.update(extra_headers)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(provider.userinfo_url, headers=headers)
        resp.raise_for_status()
        return resp.json()
