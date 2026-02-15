"""Tests for password reset functionality."""

import hashlib
import secrets
from datetime import datetime, timedelta

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def _create_test_token(db_session, user_id, expired=False, used=False):
    """Helper to create a password reset token for testing."""
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    if expired:
        expires_at = datetime.utcnow() - timedelta(minutes=5)
    else:
        expires_at = datetime.utcnow() + timedelta(minutes=30)
    token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        is_used=used,
        expires_at=expires_at,
    )
    db_session.add(token)
    db_session.flush()
    return raw_token, token


# ============================================================
# TestForgotPassword
# ============================================================


class TestForgotPassword:
    def test_forgot_password_known_email(self, raw_client, db_session):
        """Request with known email returns 200."""
        res = raw_client.post(
            "/api/auth/forgot-password",
            json={"email": "default_user@example.com"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "detail" in data

        # Verify token was created
        token = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == 1).first()
        assert token is not None
        assert token.is_used is False

    def test_forgot_password_unknown_email(self, raw_client, db_session):
        """Request with unknown email returns same 200 (no enumeration)."""
        count_before = db_session.query(PasswordResetToken).count()
        res = raw_client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "detail" in data

        # Verify no new token was created
        count_after = db_session.query(PasswordResetToken).count()
        assert count_after == count_before

    def test_forgot_password_rate_limit(self, raw_client, db_session):
        """Rate limiting prevents excessive requests."""
        # Create 3 tokens (max)
        for _ in range(3):
            raw_client.post(
                "/api/auth/forgot-password",
                json={"email": "default_user@example.com"},
            )

        # 4th request should succeed (200) but not create a token
        res = raw_client.post(
            "/api/auth/forgot-password",
            json={"email": "default_user@example.com"},
        )
        assert res.status_code == 200

        # Should only have 3 tokens
        token_count = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == 1).count()
        assert token_count == 3

    def test_forgot_password_invalid_email_format(self, raw_client):
        """Invalid email format returns 422."""
        res = raw_client.post(
            "/api/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert res.status_code == 422

    def test_forgot_password_inactive_user(self, raw_client, db_session):
        """Inactive user gets same 200 response but no token."""
        user = db_session.query(User).filter(User.id == 1).first()
        user.is_active = False
        db_session.flush()

        count_before = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == 1).count()
        res = raw_client.post(
            "/api/auth/forgot-password",
            json={"email": "default_user@example.com"},
        )
        assert res.status_code == 200

        # No new token created for inactive user
        count_after = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == 1).count()
        assert count_after == count_before


# ============================================================
# TestValidateResetToken
# ============================================================


class TestValidateResetToken:
    def test_validate_valid_token(self, raw_client, db_session):
        """Valid token returns valid=true."""
        raw_token, _ = _create_test_token(db_session, user_id=1)
        res = raw_client.post(
            "/api/auth/validate-reset-token",
            json={"token": raw_token},
        )
        assert res.status_code == 200
        assert res.json()["valid"] is True

    def test_validate_expired_token(self, raw_client, db_session):
        """Expired token returns valid=false."""
        raw_token, _ = _create_test_token(db_session, user_id=1, expired=True)
        res = raw_client.post(
            "/api/auth/validate-reset-token",
            json={"token": raw_token},
        )
        assert res.status_code == 200
        assert res.json()["valid"] is False

    def test_validate_used_token(self, raw_client, db_session):
        """Used token returns valid=false."""
        raw_token, _ = _create_test_token(db_session, user_id=1, used=True)
        res = raw_client.post(
            "/api/auth/validate-reset-token",
            json={"token": raw_token},
        )
        assert res.status_code == 200
        assert res.json()["valid"] is False

    def test_validate_invalid_token(self, raw_client):
        """Non-existent token returns valid=false."""
        res = raw_client.post(
            "/api/auth/validate-reset-token",
            json={"token": "invalid-token-value"},
        )
        assert res.status_code == 200
        assert res.json()["valid"] is False


# ============================================================
# TestResetPassword
# ============================================================


class TestResetPassword:
    def test_reset_password_success(self, raw_client, db_session):
        """Successful password reset."""
        raw_token, _ = _create_test_token(db_session, user_id=1)
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123"},
        )
        assert res.status_code == 200
        assert "detail" in res.json()

    def test_reset_password_unlocks_account(self, raw_client, db_session):
        """Password reset unlocks a locked account."""
        user = db_session.query(User).filter(User.id == 1).first()
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        db_session.flush()

        raw_token, _ = _create_test_token(db_session, user_id=1)
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123"},
        )
        assert res.status_code == 200

        db_session.refresh(user)
        assert user.locked_until is None

    def test_reset_password_invalidates_other_tokens(self, raw_client, db_session):
        """Password reset invalidates all other tokens for the user."""
        raw_token1, token1 = _create_test_token(db_session, user_id=1)
        _raw_token2, token2 = _create_test_token(db_session, user_id=1)

        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token1, "new_password": "NewPass123"},
        )
        assert res.status_code == 200

        db_session.refresh(token1)
        db_session.refresh(token2)
        assert token1.is_used is True
        assert token2.is_used is True

    def test_reset_password_increments_session_version(self, raw_client, db_session):
        """Password reset increments session_version."""
        user = db_session.query(User).filter(User.id == 1).first()
        old_version = user.session_version

        raw_token, _ = _create_test_token(db_session, user_id=1)
        raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123"},
        )

        db_session.refresh(user)
        assert user.session_version == old_version + 1

    def test_reset_password_expired_token(self, raw_client, db_session):
        """Expired token returns 404."""
        raw_token, _ = _create_test_token(db_session, user_id=1, expired=True)
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123"},
        )
        assert res.status_code == 404

    def test_reset_password_used_token(self, raw_client, db_session):
        """Used token returns 404."""
        raw_token, _ = _create_test_token(db_session, user_id=1, used=True)
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123"},
        )
        assert res.status_code == 404

    def test_reset_password_invalid_token(self, raw_client):
        """Invalid token returns 404."""
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": "bogus", "new_password": "NewPass123"},
        )
        assert res.status_code == 404

    def test_reset_password_weak_password(self, raw_client, db_session):
        """Weak password returns 400."""
        raw_token, _ = _create_test_token(db_session, user_id=1)
        res = raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "short"},
        )
        assert res.status_code == 400

    def test_reset_then_login_with_new_password(self, raw_client, db_session):
        """After reset, login works with new password."""
        raw_token, _ = _create_test_token(db_session, user_id=1)
        raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "BrandNew99"},
        )

        # Login with new password
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "BrandNew99"},
        )
        assert res.status_code == 200

    def test_reset_then_old_password_fails(self, raw_client, db_session):
        """After reset, old password no longer works."""
        raw_token, _ = _create_test_token(db_session, user_id=1)
        raw_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "BrandNew99"},
        )

        # Login with old password should fail
        res = raw_client.post(
            "/api/auth/login",
            json={"email": "default_user@example.com", "password": "testpass"},
        )
        assert res.status_code == 401


# ============================================================
# TestForgotPasswordPages
# ============================================================


class TestForgotPasswordPages:
    def test_forgot_password_page_accessible(self, raw_client):
        """Forgot password page is accessible without auth."""
        res = raw_client.get("/forgot-password")
        assert res.status_code == 200
        assert "Password Reset" in res.text

    def test_reset_password_page_accessible(self, raw_client):
        """Reset password page is accessible without auth."""
        res = raw_client.get("/reset-password?token=test")
        assert res.status_code == 200
        assert "Reset Password" in res.text

    def test_forgot_password_page_no_auth_redirect(self, raw_client):
        """Forgot password page does not redirect to login."""
        res = raw_client.get("/forgot-password", follow_redirects=False)
        assert res.status_code == 200

    def test_reset_password_page_no_auth_redirect(self, raw_client):
        """Reset password page does not redirect to login."""
        res = raw_client.get("/reset-password", follow_redirects=False)
        assert res.status_code == 200
