"""Tests for Group feature."""

from app.models.group import Group
from app.models.user import User


def _seed_group(db_session, name="Test Group", sort_order=1):
    group = Group(name=name, description="test", sort_order=sort_order)
    db_session.add(group)
    db_session.flush()
    return group


class TestGroupCRUD:
    """Group CRUD operations (admin only for CUD)."""

    def test_list_groups(self, client):
        resp = client.get("/api/groups/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # At least 3 seeded groups exist (names may have been edited in live DB)
        assert len(data) >= 3

    def test_create_group_admin(self, client):
        resp = client.post(
            "/api/groups/",
            json={
                "name": "テストグループ",
                "description": "テスト用",
                "sort_order": 10,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "テストグループ"
        assert data["description"] == "テスト用"
        assert data["sort_order"] == 10
        assert data["member_count"] == 0

    def test_create_group_non_admin(self, client_user2):
        resp = client_user2.post(
            "/api/groups/",
            json={
                "name": "不正なグループ",
            },
        )
        assert resp.status_code == 403

    def test_create_group_duplicate_name(self, client):
        client.post("/api/groups/", json={"name": "UniqueGroup"})
        resp = client.post("/api/groups/", json={"name": "UniqueGroup"})
        assert resp.status_code == 400

    def test_update_group(self, client, db_session):
        group = _seed_group(db_session, name="Update Me Group")
        resp = client.put(
            f"/api/groups/{group.id}",
            json={
                "name": "Updated Group",
                "sort_order": 99,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Group"
        assert resp.json()["sort_order"] == 99

    def test_delete_group(self, client, db_session):
        group = _seed_group(db_session, name="Delete Me Group")
        resp = client.delete(f"/api/groups/{group.id}")
        assert resp.status_code == 204
        # Should be gone from list
        groups = client.get("/api/groups/")
        names = [g["name"] for g in groups.json()]
        assert "Delete Me Group" not in names

    def test_delete_group_clears_user_group(self, client, db_session):
        group = _seed_group(db_session, name="ClearGroup")
        # Assign group to default user
        user = db_session.query(User).filter(User.id == 1).first()
        user.group_id = group.id
        db_session.flush()

        # Delete group
        resp = client.delete(f"/api/groups/{group.id}")
        assert resp.status_code == 204

        # User's group_id should be NULL (SET NULL cascade)
        db_session.expire(user)
        assert user.group_id is None


class TestUserGroup:
    """User-group assignment via PUT /api/users/{id}."""

    def test_admin_assign_group(self, client, db_session):
        group = _seed_group(db_session, name="AssignGroup")
        resp = client.put("/api/users/1", json={"group_id": group.id})
        assert resp.status_code == 200
        assert resp.json()["group_id"] == group.id
        assert resp.json()["group_name"] == "AssignGroup"

    def test_admin_unassign_group(self, client, db_session):
        group = _seed_group(db_session, name="UnassignGroup")
        # First assign
        user = db_session.query(User).filter(User.id == 1).first()
        user.group_id = group.id
        db_session.flush()

        # Then unassign via API
        resp = client.put("/api/users/1", json={"group_id": None})
        assert resp.status_code == 200
        assert resp.json()["group_id"] is None
        assert resp.json()["group_name"] is None

    def test_non_admin_cannot_change_group(self, client_user2):
        resp = client_user2.put("/api/users/2", json={"group_id": 1})
        # Non-admin can only change display_name; group_id is filtered out → ForbiddenError
        assert resp.status_code == 403

    def test_user_response_includes_group_name(self, client, db_session):
        group = _seed_group(db_session, name="ResponseGroup")
        user = db_session.query(User).filter(User.id == 1).first()
        user.group_id = group.id
        db_session.flush()

        resp = client.get("/api/users/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == group.id
        assert data["group_name"] == "ResponseGroup"
