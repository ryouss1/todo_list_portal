import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL, SECRET_KEY
from app.core.security import hash_password
from app.database import get_db
from main import app

# Use the same DB but with transaction rollback for test isolation
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pre-compute once (bcrypt is slow per call)
TEST_PASSWORD = "testpass"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)

# Session cookie signer (matches Starlette SessionMiddleware internal format)
_SESSION_SIGNER = TimestampSigner(str(SECRET_KEY))


def _make_session_cookie(data: dict) -> str:
    """Create a signed session cookie value (same format as Starlette SessionMiddleware)."""
    payload = base64.b64encode(json.dumps(data).encode("utf-8"))
    return _SESSION_SIGNER.sign(payload).decode("utf-8")


@pytest.fixture()
def db_session():
    """Create a DB session that rolls back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Ensure default user exists in the session
    from app.models.user import User

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
    transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db_session):
    from app.models.user import User

    return db_session.query(User).filter(User.id == 1).first()


@pytest.fixture()
def client(db_session):
    """Create a test client with overridden DB dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.deps import get_current_user_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    with TestClient(app, cookies={"session": _make_session_cookie({"user_id": 1, "session_version": 1})}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(db_session):
    """Test client without auth override (for auth tests)."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def other_user(db_session):
    """Create a second user (user_id=2) for authorization tests."""
    from app.models.user import User

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
def client_user2(db_session, other_user):
    """Test client authenticated as user_id=2."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.deps import get_current_user_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 2
    with TestClient(app, cookies={"session": _make_session_cookie({"user_id": 2, "session_version": 1})}) as c:
        yield c
    app.dependency_overrides.clear()
