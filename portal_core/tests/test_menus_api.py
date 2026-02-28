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


def test_get_role_visibility_empty(client):
    """GET /api/menus/{id}/role-visibility returns empty list for new menu."""
    r = client.post("/api/menus/", json={"name": "rv_test_menu", "label": "RV", "path": "/rv-test"})
    menu_id = r.json()["id"]
    r2 = client.get(f"/api/menus/{menu_id}/role-visibility")
    assert r2.status_code == 200
    assert r2.json() == []


def test_put_role_visibility(client):
    """PUT /api/menus/{id}/role-visibility sets role visibility entries."""
    r = client.post("/api/menus/", json={"name": "rv_put_menu", "label": "RVP", "path": "/rvp"})
    menu_id = r.json()["id"]
    r_role = client.post("/api/roles/", json={"name": "rv_put_role", "display_name": "RVP"})
    role_id = r_role.json()["id"]

    r2 = client.put(
        f"/api/menus/{menu_id}/role-visibility",
        json={"items": [{"id": role_id, "kino_kbn": 0}]},
    )
    assert r2.status_code == 200
    rows = client.get(f"/api/menus/{menu_id}/role-visibility").json()
    assert any(row["role_id"] == role_id and row["kino_kbn"] == 0 for row in rows)


def test_get_department_visibility_empty(client):
    """GET /api/menus/{id}/department-visibility returns empty list."""
    r = client.post("/api/menus/", json={"name": "dv_test_menu", "label": "DV", "path": "/dv-test"})
    menu_id = r.json()["id"]
    r2 = client.get(f"/api/menus/{menu_id}/department-visibility")
    assert r2.status_code == 200
    assert r2.json() == []


def test_put_department_visibility(client):
    """PUT /api/menus/{id}/department-visibility sets dept visibility entries."""
    r = client.post("/api/menus/", json={"name": "dv_put_menu", "label": "DVP", "path": "/dvp"})
    menu_id = r.json()["id"]
    r_dept = client.post(
        "/api/departments/",
        json={"name": "dv_put_dept", "code": "DVP"},
    )
    dept_id = r_dept.json()["id"]

    r2 = client.put(
        f"/api/menus/{menu_id}/department-visibility",
        json={"items": [{"id": dept_id, "kino_kbn": 1}]},
    )
    assert r2.status_code == 200
    rows = client.get(f"/api/menus/{menu_id}/department-visibility").json()
    assert any(row["department_id"] == dept_id and row["kino_kbn"] == 1 for row in rows)


def test_get_user_visibility_empty(client):
    """GET /api/menus/{id}/user-visibility returns empty list."""
    r = client.post("/api/menus/", json={"name": "uv_test_menu", "label": "UV", "path": "/uv-test"})
    menu_id = r.json()["id"]
    r2 = client.get(f"/api/menus/{menu_id}/user-visibility")
    assert r2.status_code == 200
    assert r2.json() == []


def test_put_user_visibility(client):
    """PUT /api/menus/{id}/user-visibility sets user visibility entry (admin)."""
    r = client.post("/api/menus/", json={"name": "uv_put_menu", "label": "UVP", "path": "/uvp"})
    menu_id = r.json()["id"]

    r2 = client.put(
        f"/api/menus/{menu_id}/user-visibility",
        json={"items": [{"id": 1, "kino_kbn": 0}]},
    )
    assert r2.status_code == 200
    rows = client.get(f"/api/menus/{menu_id}/user-visibility").json()
    assert any(row["user_id"] == 1 and row["kino_kbn"] == 0 for row in rows)


def test_get_my_visibility(client):
    """GET /api/menus/my-visibility returns current user's overrides."""
    r = client.get("/api/menus/my-visibility")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_put_my_visibility(client):
    """PUT /api/menus/my-visibility updates self-service visibility."""
    r = client.post("/api/menus/", json={"name": "mv_self_menu", "label": "MVS", "path": "/mvs"})
    menu_id = r.json()["id"]

    r2 = client.put("/api/menus/my-visibility", json={"menu_id": menu_id, "kino_kbn": 0})
    assert r2.status_code == 200

    rows = client.get("/api/menus/my-visibility").json()
    assert any(row["menu_id"] == menu_id and row["kino_kbn"] == 0 for row in rows)


def test_delete_my_visibility(client):
    """DELETE /api/menus/my-visibility/{menu_id} resets self-service entry."""
    r = client.post("/api/menus/", json={"name": "mv_reset_menu", "label": "MVR", "path": "/mvr"})
    menu_id = r.json()["id"]
    client.put("/api/menus/my-visibility", json={"menu_id": menu_id, "kino_kbn": 0})

    r2 = client.delete(f"/api/menus/my-visibility/{menu_id}")
    assert r2.status_code == 204

    rows = client.get("/api/menus/my-visibility").json()
    assert not any(row["menu_id"] == menu_id for row in rows)
