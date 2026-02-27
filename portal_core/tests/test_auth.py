class TestAuthLogin:
    def test_login_success(self, raw_client, test_user):
        res = raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == 1
        assert data["email"] == "default_user@example.com"
        assert data["display_name"] == "Default User"

    def test_login_wrong_password(self, raw_client, test_user):
        res = raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrongpass"})
        assert res.status_code == 401
        assert "Invalid" in res.json()["detail"]

    def test_login_unknown_user(self, raw_client):
        res = raw_client.post("/api/auth/login", json={"email": "nouser@example.com", "password": "anything"})
        assert res.status_code == 401

    def test_login_inactive_user(self, raw_client, db_session, test_user):
        test_user.is_active = False
        db_session.flush()
        res = raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        assert res.status_code == 401
        assert "disabled" in res.json()["detail"]


class TestAuthLogout:
    def test_logout(self, raw_client, test_user):
        # Login first
        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        res = raw_client.post("/api/auth/logout")
        assert res.status_code == 204


class TestAuthMe:
    def test_me_authenticated(self, raw_client, test_user):
        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        res = raw_client.get("/api/auth/me")
        assert res.status_code == 200
        assert res.json()["user_id"] == 1

    def test_me_unauthenticated(self, raw_client):
        res = raw_client.get("/api/auth/me")
        assert res.status_code == 401


class TestAuthMiddleware:
    def test_api_without_auth_returns_401(self, raw_client):
        res = raw_client.get("/api/users/")
        assert res.status_code == 401

    def test_page_without_auth_redirects_to_login(self, raw_client):
        res = raw_client.get("/", follow_redirects=False)
        assert res.status_code == 302
        assert "/login" in res.headers["location"]

    def test_login_page_is_public(self, raw_client):
        res = raw_client.get("/login")
        assert res.status_code == 200


class TestLoginSessionAtomic:
    def test_login_sets_all_session_fields(self, raw_client, test_user):
        """Login should set all required session fields in the cookie."""
        import base64
        import json

        from itsdangerous import TimestampSigner

        from portal_core.config import CoreConfig

        resp = raw_client.post(
            "/api/auth/login",
            json={
                "email": "default_user@example.com",
                "password": "testpass",
            },
        )
        assert resp.status_code == 200

        # Decode the session cookie to verify all keys were written
        config = CoreConfig()
        signer = TimestampSigner(str(config.SECRET_KEY))
        cookie_value = resp.cookies.get("session")
        assert cookie_value is not None, "Session cookie not set"

        payload = signer.unsign(cookie_value)
        session_data = json.loads(base64.b64decode(payload))

        # Verify all 4 required session keys are present with correct values
        assert session_data["user_id"] == test_user.id
        assert session_data["display_name"] == test_user.display_name
        assert "session_version" in session_data
        assert "locale" in session_data
