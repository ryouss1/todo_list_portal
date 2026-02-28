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
    # Response should include the stored permissions (not just echo request)
    data = r2.json()
    assert "permissions" in data
    assert any(p["resource"] == "reports" for p in data["permissions"])
    # verify via GET
    r3 = client.get(f"/api/roles/{role_id}")
    assert any(p["resource"] == "reports" for p in r3.json()["permissions"])


def test_set_role_permissions_kino_kbn_stored(client):
    """kino_kbn value from request should be persisted and returned."""
    r = client.post("/api/roles/", json={"name": "kino_role", "display_name": "Kino"})
    role_id = r.json()["id"]
    client.put(
        f"/api/roles/{role_id}/permissions",
        json=[{"resource": "wiki", "action": "edit", "kino_kbn": 2}],
    )
    r2 = client.get(f"/api/roles/{role_id}")
    perm = next(p for p in r2.json()["permissions"] if p["resource"] == "wiki")
    assert perm["kino_kbn"] == 2


def test_assign_role_to_user(client, test_user):
    r = client.post("/api/roles/", json={"name": "assign_role", "display_name": "Assign"})
    role_id = r.json()["id"]
    r2 = client.post(f"/api/users/{test_user.id}/roles", json={"role_id": role_id})
    assert r2.status_code == 200


def test_list_user_roles(client, test_user):
    r = client.post("/api/roles/", json={"name": "list_user_role", "display_name": "List User Role"})
    role_id = r.json()["id"]
    client.post(f"/api/users/{test_user.id}/roles", json={"role_id": role_id})
    r2 = client.get(f"/api/users/{test_user.id}/roles")
    assert r2.status_code == 200
    names = [role["name"] for role in r2.json()]
    assert "list_user_role" in names


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


def test_assign_role_nonexistent_role(client, test_user):
    """Assigning a non-existent role should return 404."""
    r = client.post(f"/api/users/{test_user.id}/roles", json={"role_id": 99999})
    assert r.status_code == 404


def test_revoke_role_not_assigned(client, test_user):
    """Revoking a role that was never assigned should return 404."""
    r = client.post("/api/roles/", json={"name": "unassigned_role", "display_name": "Unassigned"})
    role_id = r.json()["id"]
    r2 = client.delete(f"/api/users/{test_user.id}/roles/{role_id}")
    assert r2.status_code == 404


def test_roles_require_admin_unauthenticated(raw_client):
    """Unauthenticated request to roles API should return 401."""
    r = raw_client.get("/api/roles/")
    assert r.status_code == 401
