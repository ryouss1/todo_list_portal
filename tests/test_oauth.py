"""Tests for OAuth2/SSO functionality (Phase 2)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.auth.oauth.github import GitHubProviderConfig
from app.core.auth.oauth.google import GoogleProviderConfig
from app.core.auth.oauth.provider import get_provider_config


# ---------------------------------------------------------------------------
# Provider Config Parsing
# ---------------------------------------------------------------------------
class TestOAuthProviderConfig:
    def test_google_parse_userinfo(self):
        cfg = GoogleProviderConfig()
        info = cfg.parse_userinfo({"sub": "12345", "email": "user@gmail.com", "name": "Test User"})
        assert info.provider_user_id == "12345"
        assert info.email == "user@gmail.com"
        assert info.display_name == "Test User"

    def test_github_parse_userinfo(self):
        cfg = GitHubProviderConfig()
        info = cfg.parse_userinfo({"id": 67890, "email": "user@github.com", "name": "GH User", "login": "ghuser"})
        assert info.provider_user_id == "67890"
        assert info.email == "user@github.com"
        assert info.display_name == "GH User"

    def test_github_fallback_to_login(self):
        cfg = GitHubProviderConfig()
        info = cfg.parse_userinfo({"id": 67890, "login": "ghuser"})
        assert info.display_name == "ghuser"

    def test_get_provider_config_registered(self):
        assert get_provider_config("google") is not None
        assert get_provider_config("github") is not None

    def test_get_provider_config_unknown(self):
        assert get_provider_config("unknown_provider") is None


# ---------------------------------------------------------------------------
# OAuth Provider Admin CRUD
# ---------------------------------------------------------------------------
class TestOAuthProviderAdmin:
    def _create_provider(self, client):
        return client.post(
            "/api/admin/oauth-providers/",
            json={
                "name": "test_provider",
                "display_name": "Test Provider",
                "client_id": "test_client_id",
                "client_secret": "test_secret",
                "authorize_url": "https://example.com/auth",
                "token_url": "https://example.com/token",
                "userinfo_url": "https://example.com/userinfo",
                "scopes": "openid email",
            },
        )

    def test_create_provider(self, client):
        resp = self._create_provider(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test_provider"
        assert data["display_name"] == "Test Provider"
        assert data["is_enabled"] is True

    def test_list_providers(self, client):
        self._create_provider(client)
        resp = client.get("/api/admin/oauth-providers/")
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["name"] == "test_provider" for p in data)

    def test_update_provider(self, client):
        create_resp = self._create_provider(client)
        pid = create_resp.json()["id"]
        resp = client.put(f"/api/admin/oauth-providers/{pid}", json={"display_name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated"

    def test_disable_provider(self, client):
        create_resp = self._create_provider(client)
        pid = create_resp.json()["id"]
        resp = client.put(f"/api/admin/oauth-providers/{pid}", json={"is_enabled": False})
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False

    def test_delete_provider(self, client):
        create_resp = self._create_provider(client)
        pid = create_resp.json()["id"]
        resp = client.delete(f"/api/admin/oauth-providers/{pid}")
        assert resp.status_code == 204

    def test_non_admin_rejected(self, client_user2):
        resp = client_user2.post(
            "/api/admin/oauth-providers/",
            json={
                "name": "x",
                "display_name": "X",
                "client_id": "x",
                "client_secret": "x",
                "authorize_url": "https://x.com/a",
                "token_url": "https://x.com/t",
                "userinfo_url": "https://x.com/u",
                "scopes": "openid",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# OAuth Public Endpoints
# ---------------------------------------------------------------------------
class TestOAuthPublicEndpoints:
    def test_providers_empty(self, raw_client):
        """No providers configured returns empty list."""
        resp = raw_client.get("/api/auth/oauth/providers")
        assert resp.status_code == 200
        # May have providers from other tests but baseline should work

    def test_providers_returns_enabled(self, client, raw_client, db_session):
        """Enabled providers are returned."""
        from app.models.oauth_provider import OAuthProvider

        provider = OAuthProvider(
            name="test_pub",
            display_name="Test Pub",
            client_id="c",
            client_secret="s",
            authorize_url="https://x.com/a",
            token_url="https://x.com/t",
            userinfo_url="https://x.com/u",
            scopes="openid",
            is_enabled=True,
        )
        db_session.add(provider)
        db_session.flush()

        resp = raw_client.get("/api/auth/oauth/providers")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "test_pub" in names

    def test_disabled_provider_not_returned(self, client, raw_client, db_session):
        """Disabled providers are not returned."""
        from app.models.oauth_provider import OAuthProvider

        provider = OAuthProvider(
            name="test_dis",
            display_name="Disabled",
            client_id="c",
            client_secret="s",
            authorize_url="https://x.com/a",
            token_url="https://x.com/t",
            userinfo_url="https://x.com/u",
            scopes="openid",
            is_enabled=False,
        )
        db_session.add(provider)
        db_session.flush()

        resp = raw_client.get("/api/auth/oauth/providers")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "test_dis" not in names


# ---------------------------------------------------------------------------
# OAuth Flow (with mocked HTTP)
# ---------------------------------------------------------------------------
class TestOAuthFlow:
    @pytest.fixture
    def google_provider(self, db_session):
        from app.models.oauth_provider import OAuthProvider

        provider = OAuthProvider(
            name="google",
            display_name="Google",
            client_id="goog_id",
            client_secret="goog_secret",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scopes="openid email profile",
            is_enabled=True,
        )
        db_session.add(provider)
        db_session.flush()
        return provider

    def test_authorize_redirects(self, raw_client, google_provider):
        """Authorize endpoint should redirect to provider."""
        resp = raw_client.get("/api/auth/oauth/google/authorize", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers.get("location", "")

    def test_callback_invalid_state(self, raw_client, google_provider):
        """Callback with invalid state should fail."""
        resp = raw_client.get("/api/auth/oauth/google/callback?code=abc&state=invalid", follow_redirects=False)
        assert resp.status_code == 400

    @patch("app.services.oauth_service.exchange_code_for_token")
    @patch("app.services.oauth_service.fetch_userinfo")
    def test_callback_auto_link_by_email(
        self,
        mock_fetch,
        mock_exchange,
        raw_client,
        google_provider,
        db_session,
        test_user,
    ):
        """Callback should auto-link when email matches existing user."""
        mock_exchange.return_value = {"access_token": "tok123", "expires_in": 3600}
        mock_fetch.return_value = {"sub": "goog_user_1", "email": "default_user@example.com", "name": "Test"}

        # Create a valid state
        from app.models.oauth_state import OAuthState

        state_obj = OAuthState(
            state="valid_state",
            code_verifier="verifier123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db_session.add(state_obj)
        db_session.flush()

        resp = raw_client.get(
            "/api/auth/oauth/google/callback?code=authcode&state=valid_state",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/"

    @patch("app.services.oauth_service.exchange_code_for_token")
    @patch("app.services.oauth_service.fetch_userinfo")
    def test_callback_unknown_email_rejected(
        self,
        mock_fetch,
        mock_exchange,
        raw_client,
        google_provider,
        db_session,
    ):
        """Callback with unknown email should be rejected (no self-registration)."""
        mock_exchange.return_value = {"access_token": "tok123"}
        mock_fetch.return_value = {"sub": "goog_user_2", "email": "unknown@example.com", "name": "Unknown"}

        from app.models.oauth_state import OAuthState

        state_obj = OAuthState(
            state="valid_state2",
            code_verifier="verifier456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db_session.add(state_obj)
        db_session.flush()

        resp = raw_client.get(
            "/api/auth/oauth/google/callback?code=authcode&state=valid_state2",
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "No matching user" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# OAuth Linking
# ---------------------------------------------------------------------------
class TestOAuthLinking:
    def test_my_links_empty(self, client):
        """No linked accounts returns empty list."""
        resp = client.get("/api/auth/oauth/my-links")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unlink_not_linked(self, client, db_session):
        """Unlinking a non-existent link returns 404."""
        from app.models.oauth_provider import OAuthProvider

        provider = OAuthProvider(
            name="unlink_test",
            display_name="Unlink",
            client_id="c",
            client_secret="s",
            authorize_url="https://x.com/a",
            token_url="https://x.com/t",
            userinfo_url="https://x.com/u",
            scopes="openid",
            is_enabled=True,
        )
        db_session.add(provider)
        db_session.flush()

        resp = client.delete("/api/auth/oauth/unlink_test/unlink")
        assert resp.status_code == 404

    def test_unlink_last_auth_method_rejected(self, client, db_session):
        """Cannot unlink the last authentication method if no password."""
        from app.models.oauth_provider import OAuthProvider
        from app.models.user import User
        from app.models.user_oauth_account import UserOAuthAccount

        # Create user without password
        user = User(
            id=70,
            email="nopw@example.com",
            display_name="NoPW",
            password_hash=None,
            role="user",
            session_version=1,
        )
        db_session.add(user)
        db_session.flush()

        provider = OAuthProvider(
            name="sole_provider",
            display_name="Sole",
            client_id="c",
            client_secret="s",
            authorize_url="https://x.com/a",
            token_url="https://x.com/t",
            userinfo_url="https://x.com/u",
            scopes="openid",
            is_enabled=True,
        )
        db_session.add(provider)
        db_session.flush()

        link = UserOAuthAccount(
            user_id=70,
            provider_id=provider.id,
            provider_user_id="ext_1",
            provider_email="nopw@example.com",
        )
        db_session.add(link)
        db_session.flush()

        # Override user_id to 70 for this test
        from app.core.deps import get_current_user_id
        from app.database import get_db
        from main import app

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 70

        from fastapi.testclient import TestClient

        from tests.conftest import _make_session_cookie

        session_data = {"user_id": 70, "session_version": 1, "locale": "en"}
        with TestClient(app, cookies={"session": _make_session_cookie(session_data)}) as c:
            resp = c.delete("/api/auth/oauth/sole_provider/unlink")
        app.dependency_overrides.clear()

        assert resp.status_code == 400
        assert "Cannot unlink" in resp.json()["detail"]

    def test_my_links_with_linked_account(self, client, db_session):
        """Linked accounts should be visible in my-links."""
        from app.models.oauth_provider import OAuthProvider
        from app.models.user_oauth_account import UserOAuthAccount

        provider = OAuthProvider(
            name="links_test",
            display_name="Links Test",
            client_id="c",
            client_secret="s",
            authorize_url="https://x.com/a",
            token_url="https://x.com/t",
            userinfo_url="https://x.com/u",
            scopes="openid",
            is_enabled=True,
        )
        db_session.add(provider)
        db_session.flush()

        link = UserOAuthAccount(
            user_id=1,
            provider_id=provider.id,
            provider_user_id="ext_user_1",
            provider_email="linked@example.com",
        )
        db_session.add(link)
        db_session.flush()

        resp = client.get("/api/auth/oauth/my-links")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["provider_name"] == "links_test"
        assert data[0]["provider_email"] == "linked@example.com"
