"""Tests for i18n (internationalization) support — portal_core."""

from conftest import _make_session_cookie
from fastapi.testclient import TestClient

from portal_core.core.i18n import get_translator, reload_translations, translate
from portal_core.database import get_db


class TestI18nModule:
    """Tests for portal_core/core/i18n.py translate functions."""

    def test_translate_ja_default(self):
        """Default locale (ja) returns Japanese translation."""
        result = translate("User not found", "ja")
        assert result == "\u30e6\u30fc\u30b6\u30fc\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"

    def test_translate_en(self):
        """English locale returns English text."""
        result = translate("User not found", "en")
        assert result == "User not found"

    def test_translate_unknown_locale_falls_back_to_default(self):
        """Unknown locale falls back to default locale (ja)."""
        result = translate("User not found", "xx")
        assert result == "\u30e6\u30fc\u30b6\u30fc\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"

    def test_translate_missing_key_returns_original(self):
        """Missing translation key returns original msgid."""
        result = translate("Some completely unknown string", "ja")
        assert result == "Some completely unknown string"

    def test_get_translator_returns_object(self):
        """get_translator returns a translation object for valid locale."""
        t = get_translator("en")
        assert t is not None
        assert t.gettext("User not found") == "User not found"

    def test_reload_translations(self):
        """reload_translations clears and reloads translation cache."""
        reload_translations()
        # After reload, translations should still work
        result = translate("User not found", "ja")
        assert result == "\u30e6\u30fc\u30b6\u30fc\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"


class TestLocaleMiddleware:
    """Tests for locale middleware setting request.state.locale."""

    def test_default_locale_is_ja(self, core_app, db_session):
        """Middleware sets default locale to 'ja' when no session locale."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        # Session without locale key -> default is ja
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            # HTML lang attribute should be 'ja' (default)
            assert 'lang="ja"' in resp.text
        core_app.dependency_overrides.clear()

    def test_locale_en_from_session(self, core_app, db_session):
        """Middleware reads locale from session cookie."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert 'lang="en"' in resp.text
        core_app.dependency_overrides.clear()


class TestErrorMessageTranslation:
    """Tests for error message translation via exception handler."""

    def test_error_translated_to_japanese(self, core_app, db_session):
        """Error messages are translated to Japanese when locale=ja."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "ja"})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            # Request a non-existent user (will raise NotFoundError("User not found"))
            resp = c.get("/api/users/99999")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "\u30e6\u30fc\u30b6\u30fc\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"
        core_app.dependency_overrides.clear()

    def test_error_in_english(self, core_app, db_session):
        """Error messages stay English when locale=en."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            resp = c.get("/api/users/99999")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "User not found"
        core_app.dependency_overrides.clear()


class TestPageTranslation:
    """Tests for page content translation via Jinja2 i18n."""

    def test_page_contains_japanese_when_locale_ja(self, core_app, db_session):
        """Pages render Japanese content when locale=ja."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "ja"})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            # Navigation should show Japanese text
            assert "\u30c0\u30c3\u30b7\u30e5\u30dc\u30fc\u30c9" in resp.text
        core_app.dependency_overrides.clear()

    def test_page_contains_english_when_locale_en(self, core_app, db_session):
        """Pages render English content when locale=en."""

        def override_get_db():
            yield db_session

        from portal_core.core.deps import get_current_user_id

        core_app.dependency_overrides[get_db] = override_get_db
        core_app.dependency_overrides[get_current_user_id] = lambda: 1
        cookie = _make_session_cookie({"user_id": 1, "session_version": 1, "locale": "en"})
        with TestClient(core_app, cookies={"session": cookie}) as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert "Dashboard" in resp.text
        core_app.dependency_overrides.clear()

    def test_login_page_default_japanese(self, core_app, db_session):
        """Login page renders in default locale (ja)."""

        def override_get_db():
            yield db_session

        core_app.dependency_overrides[get_db] = override_get_db
        with TestClient(core_app) as c:
            resp = c.get("/login")
            assert resp.status_code == 200
            # Login page should contain Japanese login text
            assert "\u30ed\u30b0\u30a4\u30f3" in resp.text
        core_app.dependency_overrides.clear()
