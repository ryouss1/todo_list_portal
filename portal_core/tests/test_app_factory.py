"""Tests for PortalApp factory — nav item registration and single-source behavior."""

import pytest

from portal_core.app_factory import NavItem, PortalApp
from portal_core.config import CoreConfig


@pytest.fixture()
def portal():
    """Build a minimal PortalApp (without calling build()) for structural tests."""
    config = CoreConfig()
    p = PortalApp(config, title="Test Portal")
    p.setup_core()
    return p


def test_register_nav_item_appends_to_nav_items(portal):
    """Registered nav items must appear in _nav_items."""
    item = NavItem("Test", "/test", "bi-star", sort_order=50)
    initial_count = len(portal._nav_items)
    portal.register_nav_item(item)
    assert len(portal._nav_items) == initial_count + 1
    assert item in portal._nav_items


def test_setup_core_adds_dashboard_and_users(portal):
    """setup_core() must register Dashboard and Users nav items."""
    paths = [item.path for item in portal._nav_items]
    assert "/" in paths
    assert "/users" in paths


def test_no_seed_hooks_nav_attribute(portal):
    """PortalApp must not have a _seed_hooks_nav attribute after refactoring."""
    assert not hasattr(portal, "_seed_hooks_nav"), "_seed_hooks_nav still exists — duplicate list was not removed"


def test_nav_items_is_single_source_of_truth(portal):
    """After registering items, _nav_items is the only nav list."""
    item = NavItem("Extra", "/extra", sort_order=200)
    portal.register_nav_item(item)
    # Verify _nav_items contains everything
    paths = [i.path for i in portal._nav_items]
    assert "/extra" in paths
    assert "/" in paths
    assert "/users" in paths
