"""Fixtures for portal_core standalone tests.

Uses a minimal PortalApp (no app-specific routers/models) so that
portal_core can be tested independently.
"""

import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import Column, Integer, Table, create_engine
from sqlalchemy.orm import sessionmaker

from portal_core.config import CoreConfig
from portal_core.core.security import hash_password
from portal_core.database import Base, get_db
from portal_core.models.user import User

# ---------------------------------------------------------------------------
# Register stub tables for app-specific FK references in core models.
# User.default_preset_id references attendance_presets.id which is app-specific.
# We register a minimal table in metadata so SQLAlchemy can resolve the FK
# without importing app models.
# ---------------------------------------------------------------------------
if "attendance_presets" not in Base.metadata.tables:
    Table("attendance_presets", Base.metadata, Column("id", Integer, primary_key=True))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

config = CoreConfig()
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pre-compute once (bcrypt is slow per call)
TEST_PASSWORD = "testpass"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)

# Session cookie signer (matches Starlette SessionMiddleware internal format)
_SESSION_SIGNER = TimestampSigner(str(config.SECRET_KEY))


def _make_session_cookie(data: dict) -> str:
    """Create a signed session cookie value (same format as Starlette SessionMiddleware)."""
    payload = base64.b64encode(json.dumps(data).encode("utf-8"))
    return _SESSION_SIGNER.sign(payload).decode("utf-8")


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def core_app():
    """Build a portal_core-only FastAPI app for testing.

    Contains: auth, users, departments, OAuth routers + core pages (login, users, dashboard).
    Also registers a test WebSocket endpoint at /ws/test for WS infrastructure tests.
    Does NOT contain app-specific routers (todos, tasks, etc.).
    """
    from portal_core.app_factory import PortalApp
    from portal_core.services.websocket_manager import WebSocketManager

    test_ws_manager = WebSocketManager()

    portal = PortalApp(config, title="Test Portal Core")
    portal.setup_core()
    portal.register_websocket("/ws/test", test_ws_manager)
    app = portal.build()
    app.state.test_ws_manager = test_ws_manager
    return app


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Create a DB session that rolls back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Ensure default user exists in the session
    user = session.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email="default_user@example.com",
            display_name="Default User",
            password_hash=TEST_PASSWORD_HASH,
            role="admin",
        )
        session.add(user)
        session.flush()
    else:
        user.email = "default_user@example.com"
        user.password_hash = TEST_PASSWORD_HASH
        user.role = "admin"
        user.is_active = True
        user.session_version = 1
        session.flush()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db_session):
    """Return the default user (id=1)."""
    return db_session.query(User).filter(User.id == 1).first()


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(core_app, db_session):
    """Authenticated test client (user_id=1, role=admin)."""
    from fastapi_csrf_protect import CsrfProtect

    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    core_app.dependency_overrides[get_current_user_id] = lambda: 1

    csrf_protect = CsrfProtect()
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    session_data = {"user_id": 1, "session_version": 1, "locale": "en"}
    cookies = {
        "session": _make_session_cookie(session_data),
        "fastapi-csrf-token": signed_token,
    }
    with TestClient(core_app, cookies=cookies, headers={"X-CSRF-Token": csrf_token}) as c:
        yield c
    core_app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(core_app, db_session):
    """Unauthenticated test client (for auth/login tests)."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    with TestClient(core_app, cookies={"session": _make_session_cookie({"locale": "en"})}) as c:
        yield c
    core_app.dependency_overrides.clear()


@pytest.fixture()
def other_user(db_session):
    """Create a second user (user_id=2) for authorization tests."""
    user = User(
        id=2,
        email="other_user@example.com",
        display_name="Other User",
        password_hash=TEST_PASSWORD_HASH,
        session_version=1,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def client_user2(core_app, db_session, other_user):
    """Authenticated test client (user_id=2, role=user)."""
    from fastapi_csrf_protect import CsrfProtect

    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    core_app.dependency_overrides[get_current_user_id] = lambda: 2

    csrf_protect = CsrfProtect()
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    session_data = {"user_id": 2, "session_version": 1, "locale": "en"}
    cookies = {
        "session": _make_session_cookie(session_data),
        "fastapi-csrf-token": signed_token,
    }
    with TestClient(core_app, cookies=cookies, headers={"X-CSRF-Token": csrf_token}) as c:
        yield c
    core_app.dependency_overrides.clear()
