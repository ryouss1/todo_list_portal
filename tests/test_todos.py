class TestTodoAPI:
    def test_list_todos_empty(self, client):
        resp = client.get("/api/todos/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_todo(self, client):
        resp = client.post(
            "/api/todos/",
            json={
                "title": "Test Todo",
                "description": "Test description",
                "priority": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Todo"
        assert data["description"] == "Test description"
        assert data["priority"] == 1
        assert data["is_completed"] is False
        assert data["user_id"] == 1

    def test_create_todo_minimal(self, client):
        resp = client.post("/api/todos/", json={"title": "Minimal"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minimal"
        assert data["priority"] == 0
        assert data["due_date"] is None

    def test_get_todo(self, client):
        create_resp = client.post("/api/todos/", json={"title": "Get me"})
        todo_id = create_resp.json()["id"]

        resp = client.get(f"/api/todos/{todo_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get me"

    def test_get_todo_not_found(self, client):
        resp = client.get("/api/todos/99999")
        assert resp.status_code == 404

    def test_update_todo(self, client):
        create_resp = client.post("/api/todos/", json={"title": "Old title"})
        todo_id = create_resp.json()["id"]

        resp = client.put(f"/api/todos/{todo_id}", json={"title": "New title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New title"

    def test_delete_todo(self, client):
        create_resp = client.post("/api/todos/", json={"title": "Delete me"})
        todo_id = create_resp.json()["id"]

        resp = client.delete(f"/api/todos/{todo_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/todos/{todo_id}")
        assert resp.status_code == 404

    def test_toggle_todo(self, client):
        create_resp = client.post("/api/todos/", json={"title": "Toggle me"})
        todo_id = create_resp.json()["id"]
        assert create_resp.json()["is_completed"] is False

        resp = client.patch(f"/api/todos/{todo_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

        resp = client.patch(f"/api/todos/{todo_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is False

    def test_create_todo_with_due_date(self, client):
        resp = client.post(
            "/api/todos/",
            json={
                "title": "With due date",
                "due_date": "2026-03-01",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["due_date"] == "2026-03-01"

    def test_create_todo_missing_title(self, client):
        resp = client.post("/api/todos/", json={"description": "No title"})
        assert resp.status_code == 422

    def test_create_todo_default_visibility(self, client):
        resp = client.post("/api/todos/", json={"title": "Default vis"})
        assert resp.status_code == 201
        assert resp.json()["visibility"] == "private"

    def test_create_todo_public(self, client):
        resp = client.post("/api/todos/", json={"title": "Public todo", "visibility": "public"})
        assert resp.status_code == 201
        assert resp.json()["visibility"] == "public"

    def test_create_todo_invalid_visibility(self, client):
        resp = client.post("/api/todos/", json={"title": "Bad vis", "visibility": "invalid"})
        assert resp.status_code == 422

    def test_update_visibility(self, client):
        resp = client.post("/api/todos/", json={"title": "Change vis"})
        todo_id = resp.json()["id"]
        assert resp.json()["visibility"] == "private"

        resp = client.put(f"/api/todos/{todo_id}", json={"visibility": "public"})
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "public"

    def test_list_public_todos_empty(self, client, db_session):
        # Clean up any stale public todos to avoid DB interference
        from app.models.todo import Todo

        db_session.query(Todo).filter(Todo.visibility == "public").delete()
        db_session.flush()

        resp = client.get("/api/todos/public")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_public_todos(self, client, db_session):
        # Clean up any stale public todos to avoid DB interference
        from app.models.todo import Todo

        db_session.query(Todo).filter(Todo.visibility == "public").delete()
        db_session.flush()

        client.post("/api/todos/", json={"title": "Private", "visibility": "private"})
        client.post("/api/todos/", json={"title": "Public", "visibility": "public"})

        resp = client.get("/api/todos/public")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Public"

    def test_own_list_includes_all_visibilities(self, client):
        client.post("/api/todos/", json={"title": "Private one", "visibility": "private"})
        client.post("/api/todos/", json={"title": "Public one", "visibility": "public"})

        resp = client.get("/api/todos/")
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()]
        assert "Private one" in titles
        assert "Public one" in titles
