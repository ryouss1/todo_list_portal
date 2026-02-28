"""Tests for nav items TTL cache in PortalApp._get_filtered_nav_items."""

from unittest.mock import MagicMock, patch

from portal_core.app_factory import NavItem, PortalApp
from portal_core.config import CoreConfig


def _make_portal():
    """Build a minimal PortalApp with nav items but without full DB setup."""
    config = CoreConfig()
    portal = PortalApp(config, title="Cache Test")
    portal._nav_items = [
        NavItem("Dashboard", "/", "bi-speedometer2", sort_order=0),
        NavItem("Users", "/users", "bi-people", sort_order=1),
    ]
    return portal


class TestNavCache:
    def test_cache_is_initialized_empty(self):
        """PortalApp should have an empty _nav_cache on init."""
        portal = _make_portal()
        assert hasattr(portal, "_nav_cache")
        assert portal._nav_cache == {}

    def test_same_user_uses_cache(self):
        """Second call with same user_id should not hit DB (use cache)."""
        portal = _make_portal()
        mock_db = MagicMock()
        with (
            patch(
                "portal_core.app_factory.get_menus",
                return_value=[MagicMock()],
            ),
            patch(
                "portal_core.app_factory.get_visible_menus_for_user",
                return_value=[],
            ) as mock_visible,
            patch("portal_core.app_factory.SessionLocal", return_value=mock_db),
        ):
            portal._get_filtered_nav_items(1)
            portal._get_filtered_nav_items(1)

        # DB should only have been queried once (second call used cache)
        assert mock_visible.call_count == 1

    def test_different_users_have_separate_cache(self):
        """Cache entries for user_id=1 and user_id=2 should be independent."""
        portal = _make_portal()
        mock_db = MagicMock()
        with (
            patch(
                "portal_core.app_factory.get_menus",
                return_value=[MagicMock()],
            ),
            patch(
                "portal_core.app_factory.get_visible_menus_for_user",
                return_value=[],
            ) as mock_visible,
            patch("portal_core.app_factory.SessionLocal", return_value=mock_db),
        ):
            portal._get_filtered_nav_items(1)
            portal._get_filtered_nav_items(2)

        # DB should have been queried twice (different users = different cache slots)
        assert mock_visible.call_count == 2

    def test_cache_expires_after_ttl(self):
        """After TTL expires, the next call should re-query DB."""
        portal = _make_portal()
        mock_db = MagicMock()
        with (
            patch(
                "portal_core.app_factory.get_menus",
                return_value=[MagicMock()],
            ),
            patch(
                "portal_core.app_factory.get_visible_menus_for_user",
                return_value=[],
            ) as mock_visible,
            patch("portal_core.app_factory.SessionLocal", return_value=mock_db),
            patch("time.monotonic", side_effect=[0.0, 9999.0]),
        ):
            # Call 1: time=0.0, populates cache
            portal._get_filtered_nav_items(1)
            # Call 2: time=9999.0 (cache long expired)
            portal._get_filtered_nav_items(1)

        assert mock_visible.call_count == 2
