def test_list_roles_empty(client):
    r = client.get("/api/roles/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_role(client):
    r = client.post("/api/roles/", json={"name": "api_role", "display_name": "API Role"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "api_role"
    assert data["permissions"] == []


def test_create_role_duplicate_name(client):
    client.post("/api/roles/", json={"name": "dup_role", "display_name": "Dup"})
    r = client.post("/api/roles/", json={"name": "dup_role", "display_name": "Dup2"})
    assert r.status_code == 409


def test_update_role(client):
    r = client.post("/api/roles/", json={"name": "upd_role", "display_name": "Old"})
    role_id = r.json()["id"]
    r2 = client.put(f"/api/roles/{role_id}", json={"display_name": "New"})
    assert r2.status_code == 200
    assert r2.json()["display_name"] == "New"


def test_set_role_permissions(client):
    r = client.post("/api/roles/", json={"name": "perm_api_role", "display_name": "Perm"})
    role_id = r.json()["id"]
    r2 = client.put(
        f"/api/roles/{role_id}/permissions",
        json=[{"resource": "reports", "action": "view", "kino_kbn": 1}],
    )
    assert r2.status_code == 200
    # verify via GET
    r3 = client.get(f"/api/roles/{role_id}")
    assert any(p["resource"] == "reports" for p in r3.json()["permissions"])


def test_assign_role_to_user(client, test_user):
    r = client.post("/api/roles/", json={"name": "assign_role", "display_name": "Assign"})
    role_id = r.json()["id"]
    r2 = client.post(f"/api/users/{test_user.id}/roles", json={"role_id": role_id})
    assert r2.status_code == 200


def test_list_user_roles(client, test_user):
    r = client.get(f"/api/users/{test_user.id}/roles")
    assert r.status_code == 200


def test_revoke_user_role(client, test_user):
    r = client.post("/api/roles/", json={"name": "revoke_api", "display_name": "Revoke"})
    role_id = r.json()["id"]
    client.post(f"/api/users/{test_user.id}/roles", json={"role_id": role_id})
    r2 = client.delete(f"/api/users/{test_user.id}/roles/{role_id}")
    assert r2.status_code == 204


def test_delete_role(client):
    r = client.post("/api/roles/", json={"name": "del_role", "display_name": "Del"})
    role_id = r.json()["id"]
    r2 = client.delete(f"/api/roles/{role_id}")
    assert r2.status_code == 204


def test_delete_nonexistent_role(client):
    r = client.delete("/api/roles/99999")
    assert r.status_code == 404
