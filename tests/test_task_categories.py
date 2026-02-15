from app.models.task_category import TaskCategory


def _seed_category(db_session, category_id=1, name="テスト"):
    cat = db_session.query(TaskCategory).filter(TaskCategory.id == category_id).first()
    if not cat:
        cat = TaskCategory(id=category_id, name=name)
        db_session.add(cat)
        db_session.flush()
    return cat


class TestTaskCategoryAPI:
    def test_list_categories_empty(self, client):
        resp = client.get("/api/task-categories/")
        assert resp.status_code == 200
        # May contain seeded categories from startup
        assert isinstance(resp.json(), list)

    def test_create_category(self, client):
        resp = client.post("/api/task-categories/", json={"name": "新規カテゴリ"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新規カテゴリ"
        assert "id" in data

    def test_create_category_and_list(self, client):
        client.post("/api/task-categories/", json={"name": "Cat A"})
        client.post("/api/task-categories/", json={"name": "Cat B"})
        resp = client.get("/api/task-categories/")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Cat A" in names
        assert "Cat B" in names

    def test_update_category(self, client, db_session):
        _seed_category(db_session, category_id=100, name="Old name")
        resp = client.put("/api/task-categories/100", json={"name": "New name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New name"

    def test_delete_category(self, client, db_session):
        _seed_category(db_session, category_id=101, name="To delete")
        resp = client.delete("/api/task-categories/101")
        assert resp.status_code == 204

        resp = client.get("/api/task-categories/")
        ids = [c["id"] for c in resp.json()]
        assert 101 not in ids

    def test_update_nonexistent(self, client):
        resp = client.put("/api/task-categories/9999", json={"name": "Nope"})
        assert resp.status_code == 404

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/task-categories/9999")
        assert resp.status_code == 404


class TestTaskCategoryAuthorization:
    def test_user_can_list(self, client_user2):
        resp = client_user2.get("/api/task-categories/")
        assert resp.status_code == 200

    def test_user_cannot_create(self, client_user2):
        resp = client_user2.post("/api/task-categories/", json={"name": "Blocked"})
        assert resp.status_code == 403

    def test_user_cannot_update(self, client_user2, db_session):
        _seed_category(db_session, category_id=102, name="Admin only")
        resp = client_user2.put("/api/task-categories/102", json={"name": "Hacked"})
        assert resp.status_code == 403

    def test_user_cannot_delete(self, client_user2, db_session):
        _seed_category(db_session, category_id=103, name="Admin only")
        resp = client_user2.delete("/api/task-categories/103")
        assert resp.status_code == 403
