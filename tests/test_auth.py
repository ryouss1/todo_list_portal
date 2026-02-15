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
        res = raw_client.get("/api/todos/")
        assert res.status_code == 401

    def test_page_without_auth_redirects_to_login(self, raw_client):
        res = raw_client.get("/", follow_redirects=False)
        assert res.status_code == 302
        assert "/login" in res.headers["location"]

    def test_logs_post_is_public(self, raw_client):
        """POST /api/logs/ is public for external log ingestion."""
        res = raw_client.post(
            "/api/logs/",
            json={"system_name": "test", "log_type": "app", "severity": "INFO", "message": "test"},
        )
        assert res.status_code == 201

    def test_logs_get_requires_auth(self, raw_client):
        """GET /api/logs/ requires authentication."""
        res = raw_client.get("/api/logs/")
        assert res.status_code == 401

    def test_login_page_is_public(self, raw_client):
        res = raw_client.get("/login")
        assert res.status_code == 200
