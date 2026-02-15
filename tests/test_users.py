"""Tests for User API (ISSUE-008, ISSUE-010)."""


class TestUserAPI:
    def test_list_users(self, client):
        resp = client.get("/api/users/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        emails = [u["email"] for u in data]
        assert "default_user@example.com" in emails

    def test_create_user(self, client):
        resp = client.post(
            "/api/users/",
            json={"email": "newuser@example.com", "display_name": "New User", "password": "Secret123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"
        assert data["is_active"] is True
        assert "password" not in data
        assert "password_hash" not in data

    def test_create_user_password_hashed(self, client, db_session):
        client.post(
            "/api/users/",
            json={"email": "hashtest@example.com", "display_name": "Hash Test", "password": "MyPassword1"},
        )
        from app.models.user import User

        user = db_session.query(User).filter(User.email == "hashtest@example.com").first()
        assert user is not None
        assert user.password_hash != "mypassword"
        assert user.password_hash.startswith("$2b$")

    def test_create_user_missing_password(self, client):
        resp = client.post(
            "/api/users/",
            json={"email": "nopw@example.com", "display_name": "No Password"},
        )
        assert resp.status_code == 422

    def test_create_user_duplicate_email(self, client):
        client.post(
            "/api/users/",
            json={"email": "dupuser@example.com", "display_name": "First", "password": "DupPass1"},
        )
        resp = client.post(
            "/api/users/",
            json={"email": "dupuser@example.com", "display_name": "Second", "password": "DupPass2"},
        )
        assert resp.status_code in (400, 409, 500)

    def test_get_user(self, client):
        resp = client.get("/api/users/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["email"] == "default_user@example.com"

    def test_get_user_not_found(self, client):
        resp = client.get("/api/users/99999")
        assert resp.status_code == 404

    def test_user_response_includes_role(self, client):
        """Users API response includes role field."""
        resp = client.get("/api/users/1")
        assert resp.status_code == 200
        assert "role" in resp.json()
        assert resp.json()["role"] == "admin"


class TestUserRBAC:
    """ISSUE-024+033: Non-admin users cannot create users."""

    def test_non_admin_cannot_create_user(self, client_user2):
        resp = client_user2.post(
            "/api/users/",
            json={"email": "unauthorized@example.com", "display_name": "Unauth", "password": "pass"},
        )
        assert resp.status_code == 403

    def test_non_admin_can_list_users(self, client_user2):
        resp = client_user2.get("/api/users/")
        assert resp.status_code == 200


class TestUserUpdate:
    def test_admin_update_user_display_name(self, client, db_session):
        from app.models.user import User

        user = User(id=10, email="upd_user@example.com", display_name="Old Name", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.put("/api/users/10", json={"display_name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "New Name"

    def test_admin_update_user_role(self, client, db_session):
        from app.models.user import User

        user = User(id=11, email="role_user@example.com", display_name="Role", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.put("/api/users/11", json={"role": "admin"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_admin_update_user_deactivate(self, client, db_session):
        from app.models.user import User

        user = User(id=12, email="deact_user@example.com", display_name="Deact", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.put("/api/users/12", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_user_not_found(self, client):
        resp = client.put("/api/users/99999", json={"display_name": "X"})
        assert resp.status_code == 404

    def test_admin_cannot_deactivate_self(self, client):
        resp = client.put("/api/users/1", json={"is_active": False})
        assert resp.status_code == 403


class TestUserSelfEdit:
    """Non-admin users can edit their own display_name only."""

    def test_non_admin_can_edit_own_display_name(self, client_user2):
        resp = client_user2.put("/api/users/2", json={"display_name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    def test_non_admin_cannot_edit_own_role(self, client_user2):
        resp = client_user2.put("/api/users/2", json={"role": "admin"})
        assert resp.status_code == 403

    def test_non_admin_cannot_edit_own_is_active(self, client_user2):
        resp = client_user2.put("/api/users/2", json={"is_active": False})
        assert resp.status_code == 403

    def test_non_admin_cannot_edit_other_user(self, client_user2):
        resp = client_user2.put("/api/users/1", json={"display_name": "Hacked"})
        assert resp.status_code == 403

    def test_non_admin_cannot_edit_own_email(self, client_user2):
        resp = client_user2.put("/api/users/2", json={"email": "hacked@example.com"})
        assert resp.status_code == 403


class TestUserDelete:
    def test_admin_delete_user(self, client, db_session):
        from app.models.user import User

        user = User(id=20, email="del_user@example.com", display_name="Del", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.delete("/api/users/20")
        assert resp.status_code == 204

    def test_delete_user_not_found(self, client):
        resp = client.delete("/api/users/99999")
        assert resp.status_code == 404

    def test_admin_cannot_delete_self(self, client):
        resp = client.delete("/api/users/1")
        assert resp.status_code == 403


class TestPasswordChange:
    def test_change_own_password(self, client):
        resp = client.put(
            "/api/users/me/password",
            json={"current_password": "testpass", "new_password": "NewPass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Password changed"

    def test_change_password_wrong_current(self, client):
        resp = client.put(
            "/api/users/me/password",
            json={"current_password": "wrongpass", "new_password": "NewPass123"},
        )
        assert resp.status_code == 400

    def test_admin_reset_password(self, client, db_session):
        from app.models.user import User

        user = User(id=30, email="reset_user@example.com", display_name="Reset", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.put("/api/users/30/password", json={"new_password": "ResetPass1"})
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Password reset"

    def test_non_admin_cannot_reset_others_password(self, client_user2):
        resp = client_user2.put("/api/users/1/password", json={"new_password": "Hacked123"})
        assert resp.status_code == 403


class TestUserUpdateRBAC:
    def test_non_admin_cannot_delete_user(self, client_user2):
        resp = client_user2.delete("/api/users/1")
        assert resp.status_code == 403
