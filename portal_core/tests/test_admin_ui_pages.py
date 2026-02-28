"""Tests for admin UI page routes: /roles and /menus."""


def test_roles_page_accessible_to_admin(client):
    r = client.get("/roles")
    assert r.status_code == 200
    assert "Roles" in r.text


def test_menus_page_accessible_to_admin(client):
    r = client.get("/menus")
    assert r.status_code == 200
    assert "Menus" in r.text
