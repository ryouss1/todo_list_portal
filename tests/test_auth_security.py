"""Tests for authentication security enhancements (Phase 1)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.auth.password_policy import validate_password
from app.core.exceptions import ConflictError


# ---------------------------------------------------------------------------
# Password Policy
# ---------------------------------------------------------------------------
class TestPasswordPolicy:
    def test_valid_password(self):
        """A password meeting all requirements should pass validation."""
        validate_password("SecurePass1")

    def test_too_short(self):
        with pytest.raises(ConflictError, match="at least 8"):
            validate_password("Sh0rt")

    def test_too_long(self):
        with pytest.raises(ConflictError, match="at most 128"):
            validate_password("A1" + "a" * 127)

    def test_missing_uppercase(self):
        with pytest.raises(ConflictError, match="uppercase"):
            validate_password("lowercase1")

    def test_missing_lowercase(self):
        with pytest.raises(ConflictError, match="lowercase"):
            validate_password("UPPERCASE1")

    def test_missing_digit(self):
        with pytest.raises(ConflictError, match="digit"):
            validate_password("NoDigitHere")

    def test_special_not_required_by_default(self):
        """Special characters are not required by default."""
        validate_password("NoSpecial1")

    @patch("app.core.auth.password_policy.config")
    def test_special_required_when_configured(self, mock_config):
        mock_config.PASSWORD_MIN_LENGTH = 8
        mock_config.PASSWORD_MAX_LENGTH = 128
        mock_config.PASSWORD_REQUIRE_UPPERCASE = False
        mock_config.PASSWORD_REQUIRE_LOWERCASE = False
        mock_config.PASSWORD_REQUIRE_DIGIT = False
        mock_config.PASSWORD_REQUIRE_SPECIAL = True
        with pytest.raises(ConflictError, match="special"):
            validate_password("nospecialchar")


# ---------------------------------------------------------------------------
# Password policy integration (via API)
# ---------------------------------------------------------------------------
class TestPasswordPolicyIntegration:
    def test_create_user_weak_password_rejected(self, client):
        resp = client.post(
            "/api/users/",
            json={"email": "weak@example.com", "display_name": "Weak", "password": "weak"},
        )
        assert resp.status_code == 400
        assert "at least 8" in resp.json()["detail"]

    def test_change_password_weak_rejected(self, client):
        resp = client.put(
            "/api/users/me/password",
            json={"current_password": "testpass", "new_password": "weak"},
        )
        assert resp.status_code == 400

    def test_reset_password_weak_rejected(self, client, db_session):
        from app.models.user import User

        user = User(id=50, email="reset_weak@example.com", display_name="RW", password_hash="x", role="user")
        db_session.add(user)
        db_session.flush()

        resp = client.put("/api/users/50/password", json={"new_password": "short"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
class TestRateLimiting:
    def test_under_limit_allows_login(self, raw_client, test_user):
        """A few failures should not block login."""
        for _ in range(3):
            raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrong"})
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "testpass"},
        )
        assert res.status_code == 200

    def test_at_limit_blocks_login(self, raw_client, test_user):
        """After max attempts, further attempts are blocked."""
        for _ in range(5):
            raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrong"})
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "testpass"},
        )
        assert res.status_code == 400
        assert "Too many" in res.json()["detail"]

    def test_attempts_are_recorded(self, raw_client, test_user, db_session):
        """Login attempts should be recorded in the database."""
        from app.models.login_attempt import LoginAttempt

        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrong"})
        attempts = db_session.query(LoginAttempt).filter(LoginAttempt.email == "default_user@example.com").all()
        assert len(attempts) >= 1
        assert attempts[-1].success is False

    def test_success_is_recorded(self, raw_client, test_user, db_session):
        """Successful login should be recorded."""
        from app.models.login_attempt import LoginAttempt

        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        attempts = (
            db_session.query(LoginAttempt)
            .filter(
                LoginAttempt.email == "default_user@example.com",
                LoginAttempt.success.is_(True),
            )
            .all()
        )
        assert len(attempts) >= 1


# ---------------------------------------------------------------------------
# Account Lockout
# ---------------------------------------------------------------------------
class TestAccountLockout:
    def test_locked_account_rejected(self, raw_client, test_user, db_session):
        """A locked account should be rejected even with correct password."""
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db_session.flush()
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "testpass"},
        )
        assert res.status_code == 401
        assert "locked" in res.json()["detail"]

    def test_lock_after_max_failures(self, raw_client, test_user, db_session):
        """Account should get locked after max failures."""
        for _ in range(5):
            raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrong"})
        db_session.refresh(test_user)
        assert test_user.locked_until is not None
        assert test_user.locked_until > datetime.now(timezone.utc)

    def test_admin_unlock(self, client, db_session):
        """Admin can unlock a locked account."""
        from app.models.user import User

        user = User(
            id=60,
            email="locked@example.com",
            display_name="Locked",
            password_hash="x",
            role="user",
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db_session.add(user)
        db_session.flush()

        resp = client.post("/api/users/60/unlock")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Account unlocked"

        db_session.refresh(user)
        assert user.locked_until is None

    def test_expired_lock_allows_login(self, raw_client, test_user, db_session):
        """An expired lock should allow login."""
        test_user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.flush()
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "testpass"},
        )
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# Session Invalidation
# ---------------------------------------------------------------------------
class TestSessionInvalidation:
    def test_password_change_invalidates_session(self, raw_client, test_user, db_session):
        """After password change, old session should be invalid for endpoints using Depends(get_current_user_id)."""
        # Login to get a session
        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        # Verify session works (use /api/todos/ which uses get_current_user_id)
        res = raw_client.get("/api/todos/")
        assert res.status_code == 200

        # Change password (this increments session_version)
        from app.core.security import hash_password

        test_user.password_hash = hash_password("NewPass123")
        test_user.session_version = (test_user.session_version or 1) + 1
        db_session.flush()

        # Old session should now be invalid (session_version mismatch)
        res = raw_client.get("/api/todos/")
        assert res.status_code == 401

    def test_valid_session_works(self, raw_client, test_user):
        """A valid session should continue to work."""
        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        # Use endpoint that goes through get_current_user_id
        res = raw_client.get("/api/todos/")
        assert res.status_code == 200

    def test_inactive_user_session_cleared(self, raw_client, test_user, db_session):
        """Deactivated user's session should be cleared."""
        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        res = raw_client.get("/api/todos/")
        assert res.status_code == 200

        test_user.is_active = False
        db_session.flush()

        res = raw_client.get("/api/todos/")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------
class TestAuditLogging:
    def test_login_success_audit(self, raw_client, test_user, db_session):
        """Successful login should create audit log."""
        from app.models.auth_audit_log import AuthAuditLog

        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})
        logs = (
            db_session.query(AuthAuditLog)
            .filter(
                AuthAuditLog.event_type == "login_success",
                AuthAuditLog.user_id == 1,
            )
            .all()
        )
        assert len(logs) >= 1

    def test_login_failure_audit(self, raw_client, test_user, db_session):
        """Failed login should create audit log."""
        from app.models.auth_audit_log import AuthAuditLog

        raw_client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "wrong"})
        logs = (
            db_session.query(AuthAuditLog)
            .filter(
                AuthAuditLog.event_type == "login_failure",
            )
            .all()
        )
        assert len(logs) >= 1

    def test_password_change_audit(self, client, db_session):
        """Password change should create audit log."""
        from app.models.auth_audit_log import AuthAuditLog

        client.put(
            "/api/users/me/password",
            json={"current_password": "testpass", "new_password": "NewSecure1"},
        )
        logs = (
            db_session.query(AuthAuditLog)
            .filter(
                AuthAuditLog.event_type == "password_change",
                AuthAuditLog.user_id == 1,
            )
            .all()
        )
        assert len(logs) >= 1

    def test_admin_audit_logs_endpoint(self, client, db_session):
        """Admin can query audit logs via API."""
        from app.models.auth_audit_log import AuthAuditLog

        db_session.add(AuthAuditLog(event_type="login_success", user_id=1, email="admin@example.com"))
        db_session.flush()

        resp = client.get("/api/auth/audit-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["event_type"] == "login_success"

    def test_non_admin_cannot_access_audit_logs(self, client_user2):
        resp = client_user2.get("/api/auth/audit-logs")
        assert resp.status_code == 403
