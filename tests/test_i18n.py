"""Tests for i18n (internationalization) support."""

from fastapi.testclient import TestClient

from app.core.i18n import get_translator, reload_translations, translate
from app.database import get_db
from main import app
from tests.conftest import _make_session_cookie


class TestI18nModule:
    """Tests for app/core/i18n.py translate functions."""

    def test_translate_ja_default(self):
        """Default locale (ja) returns Japanese translation."""
        result = translate("Task not found", "ja")
        assert result == "タスクが見つかりません"

    def test_translate_en(self):
        """English locale returns English text."""
        result = translate("Task not found", "en")
        assert result == "Task not found"

    def test_translate_unknown_locale_falls_back_to_default(self):
        """Unknown locale falls back to default locale (ja)."""
        result = translate("Task not found", "xx")
        assert result == "タスクが見つかりません"

    def test_translate_missing_key_returns_original(self):
        """Missing translation key returns original msgid."""
        result = translate("Some completely unknown string", "ja")
        assert result == "Some completely unknown string"

    def test_get_translator_returns_object(self):
        """get_translator returns a translation object for valid locale."""
        t = get_translator("en")
        assert t is not None
        assert t.gettext("Task not found") == "Task not found"

    def test_reload_translations(self):
        """reload_translations clears and reloads translation cache."""
        reload_translations()
        # After reload, translations should still work
        result = translate("Task not found", "ja")
        assert result == "タスクが見つかりません"


class TestLocaleMiddleware:
    """Tests for locale middleware setting request.state.locale."""

    def test_default_locale_is_ja(self, db_session):
        """Middleware sets default locale to 'ja' when no session locale."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        # Session without locale key -> default is ja
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1})
        with TestClient(app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            # HTML lang attribute should be 'ja' (default)
            assert 'lang="ja"' in resp.text
        app.dependency_overrides.clear()

    def test_locale_en_from_session(self, db_session):
        """Middleware reads locale from session cookie."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert 'lang="en"' in resp.text
        app.dependency_overrides.clear()


class TestErrorMessageTranslation:
    """Tests for error message translation via exception handler."""

    def test_error_translated_to_japanese(self, db_session):
        """Error messages are translated to Japanese when locale=ja."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "ja"})
        with TestClient(app, cookies={"session": cookie}) as c:
            # Request a non-existent todo (will raise NotFoundError("Todo not found"))
            resp = c.get("/api/todos/99999")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Todoが見つかりません"
        app.dependency_overrides.clear()

    def test_error_in_english(self, db_session):
        """Error messages stay English when locale=en."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(app, cookies={"session": cookie}) as c:
            resp = c.get("/api/todos/99999")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Todo not found"
        app.dependency_overrides.clear()


class TestPageTranslation:
    """Tests for page content translation via Jinja2 i18n."""

    def test_page_contains_japanese_when_locale_ja(self, db_session):
        """Pages render Japanese content when locale=ja."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "ja"})
        with TestClient(app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            # Navigation should show Japanese text
            assert "ダッシュボード" in resp.text
        app.dependency_overrides.clear()

    def test_page_contains_english_when_locale_en(self, db_session):
        """Pages render English content when locale=en."""

        def override_get_db():
            yield db_session

        from app.core.deps import get_current_user_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert "Dashboard" in resp.text
        app.dependency_overrides.clear()

    def test_login_page_default_japanese(self, db_session):
        """Login page renders in default locale (ja)."""

        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            resp = c.get("/login")
            assert resp.status_code == 200
            # Login page should contain Japanese login text
            assert "ログイン" in resp.text
        app.dependency_overrides.clear()


class TestLocaleJsonFiles:
    """Tests for JS translation JSON files."""

    def test_ja_json_accessible(self, client):
        """Japanese locale JSON file is accessible."""
        resp = client.get("/static/locale/ja.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "Delete" in data
        assert data["Delete"] == "削除"

    def test_en_json_accessible(self, client):
        """English locale JSON file is accessible."""
        resp = client.get("/static/locale/en.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "Delete" in data
        assert data["Delete"] == "Delete"

    def test_ja_json_has_attendance_keys(self, client):
        """Japanese JSON includes attendance-related translation keys."""
        resp = client.get("/static/locale/ja.json")
        data = resp.json()
        assert "Clock In" in data
        assert data["Clock In"] == "出勤"
        assert "Clock Out" in data
        assert data["Clock Out"] == "退勤"

    def test_en_json_has_japanese_keys_translated(self, client):
        """English JSON translates Japanese keys to English."""
        resp = client.get("/static/locale/en.json")
        data = resp.json()
        # Japanese keys should have English translations
        assert "休憩開始" in data
        assert data["休憩開始"] == "Break Start"
