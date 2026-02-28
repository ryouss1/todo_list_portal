"""Tests for admin UI page routes: /roles and /menus."""


def test_roles_page_accessible_to_admin(client):
    r = client.get("/roles")
    assert r.status_code == 200
    assert "Roles" in r.text


def test_menus_page_accessible_to_admin(client):
    r = client.get("/menus")
    assert r.status_code == 200
    assert "Menus" in r.text


def test_roles_page_accessible_to_non_admin(client_user2):
    """Non-admin users can also access the roles page (it's a UI page; API calls enforce admin-only)."""
    r = client_user2.get("/roles")
    # Page routes don't enforce admin; API endpoints do. 200 is acceptable.
    assert r.status_code == 200


def test_menus_page_accessible_to_non_admin(client_user2):
    """Non-admin users can also access the menus page (it's a UI page; API calls enforce admin-only)."""
    r = client_user2.get("/menus")
    assert r.status_code == 200
