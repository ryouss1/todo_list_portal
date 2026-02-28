def test_list_menus_empty(client):
    r = client.get("/api/menus/")
    assert r.status_code == 200


def test_create_menu(client):
    r = client.post("/api/menus/", json={"name": "api_menu", "label": "API Menu", "path": "/api-menu"})
    assert r.status_code == 201
    assert r.json()["name"] == "api_menu"


def test_create_menu_duplicate_name(client):
    client.post("/api/menus/", json={"name": "dup_menu", "label": "Dup", "path": "/dup"})
    r = client.post("/api/menus/", json={"name": "dup_menu", "label": "Dup2", "path": "/dup2"})
    assert r.status_code == 409


def test_update_menu(client):
    r = client.post("/api/menus/", json={"name": "upd_menu", "label": "Old", "path": "/old"})
    menu_id = r.json()["id"]
    r2 = client.put(f"/api/menus/{menu_id}", json={"label": "New Label"})
    assert r2.status_code == 200
    assert r2.json()["label"] == "New Label"


def test_delete_menu(client):
    r = client.post("/api/menus/", json={"name": "del_menu2", "label": "Del", "path": "/del"})
    menu_id = r.json()["id"]
    r2 = client.delete(f"/api/menus/{menu_id}")
    assert r2.status_code == 204


def test_get_my_menus(client):
    """GET /api/menus/my returns menus visible to current user."""
    r = client.get("/api/menus/my")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
