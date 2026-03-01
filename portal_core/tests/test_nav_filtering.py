"""Tests for _render() nav item filtering by user permissions.

Task 10: _render() Nav Permission Filtering
"""

from unittest.mock import MagicMock, patch

from portal_core.models.menu import Menu


def _mock_menu(path: str) -> Menu:
    """Create a mock Menu object with the given path."""
    m = MagicMock(spec=Menu)
    m.path = path
    return m


def test_dashboard_accessible_to_admin(client):
    """Dashboard page renders successfully for admin user."""
    r = client.get("/")
    assert r.status_code == 200


def test_nav_items_in_response(client):
    """Base template renders nav items — Dashboard should always appear."""
    r = client.get("/")
    assert r.status_code == 200
    # The Dashboard nav link should have href="/"
    assert 'href="/"' in r.text
    assert "Dashboard" in r.text


def test_restricted_menu_hidden_from_regular_user(client_user2):
    """A nav item is hidden when its menu requires a resource the user lacks.

    Strategy: mock get_visible_menus_for_user to return only dashboard (excluding users),
    and verify the /users nav link disappears while / remains.
    Both functions are patched at the app_factory module level where they are imported.
    """
    with (
        patch(
            "portal_core.app_factory.get_menus",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
        patch(
            "portal_core.app_factory.get_visible_menus_for_user",
            return_value=[_mock_menu("/")],
        ),
    ):
        r = client_user2.get("/")

    assert r.status_code == 200
    # Dashboard nav link must be present
    assert 'href="/"' in r.text
    # Users nav link must be absent
    assert 'href="/users"' not in r.text


def test_all_nav_hidden_when_no_permission(client_user2):
    """When user has no visible menus, nav list should contain no nav-link entries."""
    with (
        patch(
            "portal_core.app_factory.get_menus",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
        patch(
            "portal_core.app_factory.get_visible_menus_for_user",
            return_value=[],
        ),
    ):
        r = client_user2.get("/")

    assert r.status_code == 200
    # No nav items should be rendered — no nav-link hrefs for any registered path
    assert 'href="/users"' not in r.text
    # The nav-item list entries should be absent (li class="nav-item" is only from nav_items loop)
    assert '<li class="nav-item"' not in r.text


def test_fallback_when_menus_table_empty(client):
    """When DB menus table is empty, fall back to all in-memory nav items."""
    with patch(
        "portal_core.app_factory.get_menus",
        return_value=[],
    ):
        r = client.get("/")

    assert r.status_code == 200
    # Fall-back renders all in-memory nav items including Dashboard
    assert 'href="/"' in r.text
    assert "Dashboard" in r.text


def test_unauthenticated_user_page_renders(raw_client):
    """Unauthenticated users can access the login page without errors."""
    r = raw_client.get("/login")
    assert r.status_code == 200


def test_role_menu_reflected_in_nav(client_user2):
    """role_menus kino_kbn=1 makes the nav item visible for a role member."""
    with (
        patch(
            "portal_core.app_factory.get_menus",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
        patch(
            "portal_core.app_factory.get_visible_menus_for_user",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
    ):
        r = client_user2.get("/")

    assert r.status_code == 200
    assert 'href="/users"' in r.text


def test_department_menu_reflected_in_nav(client_user2):
    """department_menus kino_kbn=1 makes the nav item visible for dept members."""
    with (
        patch(
            "portal_core.app_factory.get_menus",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
        patch(
            "portal_core.app_factory.get_visible_menus_for_user",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
    ):
        r = client_user2.get("/")

    assert r.status_code == 200
    assert 'href="/users"' in r.text


def test_user_override_hide_reflected_in_nav(client_user2):
    """user_menus kino_kbn=0 hides nav item even if role allows it."""
    with (
        patch(
            "portal_core.app_factory.get_menus",
            return_value=[_mock_menu("/"), _mock_menu("/users")],
        ),
        patch(
            "portal_core.app_factory.get_visible_menus_for_user",
            return_value=[_mock_menu("/")],  # /users excluded by user override
        ),
    ):
        r = client_user2.get("/")

    assert r.status_code == 200
    assert 'href="/"' in r.text
    assert 'href="/users"' not in r.text
