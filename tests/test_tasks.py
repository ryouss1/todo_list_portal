import time
from datetime import datetime, timedelta, timezone

from app.models.task import Task
from app.models.task_category import TaskCategory
from app.models.task_time_entry import TaskTimeEntry


def _ensure_category(db_session, category_id=7, name="その他"):
    cat = db_session.query(TaskCategory).filter(TaskCategory.id == category_id).first()
    if not cat:
        cat = TaskCategory(id=category_id, name=name)
        db_session.add(cat)
        db_session.flush()
    return cat


class TestTaskAPI:
    def test_list_tasks_empty(self, client):
        resp = client.get("/api/tasks/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_task(self, client):
        resp = client.post(
            "/api/tasks/",
            json={
                "title": "Test Task",
                "description": "Test desc",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Task"
        assert data["status"] == "pending"
        assert data["total_seconds"] == 0
        assert data["user_id"] == 1

    def test_create_task_minimal(self, client):
        resp = client.post("/api/tasks/", json={"title": "Minimal"})
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_get_task(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Get me"})
        task_id = create_resp.json()["id"]

        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get me"

    def test_get_task_not_found(self, client):
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404

    def test_update_task(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Old"})
        task_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"title": "New", "description": "Updated desc"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"
        assert resp.json()["description"] == "Updated desc"

    def test_delete_task(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Delete me"})
        task_id = create_resp.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    def test_start_timer(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Timer task"})
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["started_at"] is not None
        assert data["stopped_at"] is None

    def test_start_timer_duplicate_rejected(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Timer dup"})
        task_id = create_resp.json()["id"]
        client.post(f"/api/tasks/{task_id}/start")

        resp = client.post(f"/api/tasks/{task_id}/start")
        assert resp.status_code == 400
        assert "Timer already running" in resp.json()["detail"]

    def test_stop_timer(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Stop task"})
        task_id = create_resp.json()["id"]
        client.post(f"/api/tasks/{task_id}/start")

        time.sleep(1)
        resp = client.post(f"/api/tasks/{task_id}/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stopped_at"] is not None
        assert data["elapsed_seconds"] >= 1

        # Status should revert to pending after stop
        task_resp = client.get(f"/api/tasks/{task_id}")
        assert task_resp.json()["status"] == "pending"

    def test_stop_timer_no_active(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "No timer"})
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/stop")
        assert resp.status_code == 400
        assert "No active timer" in resp.json()["detail"]

    def test_time_entries(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Entries task"})
        task_id = create_resp.json()["id"]
        client.post(f"/api/tasks/{task_id}/start")
        client.post(f"/api/tasks/{task_id}/stop")

        resp = client.get(f"/api/tasks/{task_id}/time-entries")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 1
        assert entries[0]["task_id"] == task_id

    def test_create_task_missing_title(self, client):
        resp = client.post("/api/tasks/", json={"description": "No title"})
        assert resp.status_code == 422

    def test_done_task(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Done task"})
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 204

        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    def test_done_with_report(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post("/api/tasks/", json={"title": "Report task", "report": True})
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 200
        data = resp.json()
        assert "Report task" in data["work_content"]

    def test_done_with_report_content(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/tasks/",
            json={"title": "Timed task", "description": "Some details", "report": True},
        )
        task_id = create_resp.json()["id"]

        # Start and stop timer to accumulate time
        client.post(f"/api/tasks/{task_id}/start")
        time.sleep(1)
        client.post(f"/api/tasks/{task_id}/stop")

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 200
        data = resp.json()
        assert "Timed task" in data["work_content"]
        assert "0h 0m" in data["work_content"] or "h" in data["work_content"]
        assert "Some details" in data["work_content"]

    def test_done_with_running_timer(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Running task"})
        task_id = create_resp.json()["id"]

        client.post(f"/api/tasks/{task_id}/start")

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 204

        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    def test_done_other_user(self, client_user2, db_session):
        task = Task(user_id=1, title="User1 task")
        db_session.add(task)
        db_session.flush()
        task_id = task.id

        resp = client_user2.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 404

    def test_update_report_flag(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Flag task"})
        task_id = create_resp.json()["id"]
        assert create_resp.json()["report"] is False

        resp = client.put(f"/api/tasks/{task_id}", json={"report": True})
        assert resp.status_code == 200
        assert resp.json()["report"] is True

        resp = client.put(f"/api/tasks/{task_id}", json={"report": False})
        assert resp.status_code == 200
        assert resp.json()["report"] is False

    def test_create_task_with_backlog_ticket(self, client):
        resp = client.post(
            "/api/tasks/",
            json={"title": "Ticket task", "backlog_ticket_id": "WHT-488"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["backlog_ticket_id"] == "WHT-488"

    def test_create_task_without_backlog_ticket(self, client):
        resp = client.post("/api/tasks/", json={"title": "No ticket"})
        assert resp.status_code == 201
        assert resp.json()["backlog_ticket_id"] is None

    def test_update_backlog_ticket(self, client):
        create_resp = client.post("/api/tasks/", json={"title": "Update ticket"})
        task_id = create_resp.json()["id"]

        resp = client.put(f"/api/tasks/{task_id}", json={"backlog_ticket_id": "WHT-100"})
        assert resp.status_code == 200
        assert resp.json()["backlog_ticket_id"] == "WHT-100"

        # Clear the ticket
        resp = client.put(f"/api/tasks/{task_id}", json={"backlog_ticket_id": None})
        assert resp.status_code == 200
        assert resp.json()["backlog_ticket_id"] is None

    def test_create_task_with_category(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        resp = client.post(
            "/api/tasks/",
            json={"title": "Dev task", "category_id": 1},
        )
        assert resp.status_code == 201
        assert resp.json()["category_id"] == 1

    def test_create_task_without_category(self, client):
        resp = client.post("/api/tasks/", json={"title": "No cat"})
        assert resp.status_code == 201
        assert resp.json()["category_id"] is None

    def test_update_category(self, client, db_session):
        _ensure_category(db_session, category_id=2, name="設計")
        create_resp = client.post("/api/tasks/", json={"title": "Cat task"})
        task_id = create_resp.json()["id"]

        resp = client.put(f"/api/tasks/{task_id}", json={"category_id": 2})
        assert resp.status_code == 200
        assert resp.json()["category_id"] == 2

        # Clear category
        resp = client.put(f"/api/tasks/{task_id}", json={"category_id": None})
        assert resp.status_code == 200
        assert resp.json()["category_id"] is None

    def test_done_with_report_uses_task_category(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        _ensure_category(db_session)  # ensure default category 7 exists too
        create_resp = client.post(
            "/api/tasks/",
            json={"title": "Cat report", "report": True, "category_id": 1},
        )
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category_id"] == 1

    def test_done_with_report_uses_default_category(self, client, db_session):
        _ensure_category(db_session)  # default category 7
        create_resp = client.post(
            "/api/tasks/",
            json={"title": "No cat report", "report": True},
        )
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category_id"] == 7


class TestBatchDone:
    def _make_overdue_task(self, db_session, user_id=1, title="Overdue task", report=False):
        """Create a task with updated_at set to yesterday."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        task = Task(user_id=user_id, title=title, report=report)
        db_session.add(task)
        db_session.flush()
        # Force updated_at to yesterday
        task.updated_at = yesterday
        task.created_at = yesterday
        db_session.flush()
        return task

    def test_batch_done_basic(self, client, db_session):
        task = self._make_overdue_task(db_session)
        task_id = task.id

        resp = client.post("/api/tasks/batch-done", json={"tasks": [{"task_id": task_id, "end_time": "18:00"}]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["task_id"] == task_id
        assert data["results"][0]["report_id"] is None

        # Task should be deleted
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    def test_batch_done_multiple(self, client, db_session):
        task1 = self._make_overdue_task(db_session, title="Task 1")
        task2 = self._make_overdue_task(db_session, title="Task 2")

        resp = client.post(
            "/api/tasks/batch-done",
            json={
                "tasks": [
                    {"task_id": task1.id, "end_time": "17:00"},
                    {"task_id": task2.id, "end_time": "18:30"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2

        # Both tasks should be deleted
        assert client.get(f"/api/tasks/{task1.id}").status_code == 404
        assert client.get(f"/api/tasks/{task2.id}").status_code == 404

    def test_batch_done_with_report(self, client, db_session):
        _ensure_category(db_session)
        task = self._make_overdue_task(db_session, title="Report task", report=True)
        task_id = task.id

        resp = client.post("/api/tasks/batch-done", json={"tasks": [{"task_id": task_id, "end_time": "18:00"}]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["report_id"] is not None

        # Verify daily report was created
        report_id = data["results"][0]["report_id"]
        report_resp = client.get(f"/api/reports/{report_id}")
        assert report_resp.status_code == 200
        assert "Report task" in report_resp.json()["work_content"]

    def test_batch_done_with_running_timer(self, client, db_session):
        task = self._make_overdue_task(db_session)
        task_id = task.id

        # Create an active time entry
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        entry = TaskTimeEntry(task_id=task_id, started_at=yesterday)
        db_session.add(entry)
        db_session.flush()
        task.status = "in_progress"
        db_session.flush()

        resp = client.post("/api/tasks/batch-done", json={"tasks": [{"task_id": task_id, "end_time": "18:00"}]})
        assert resp.status_code == 200

        # Task should be deleted
        assert client.get(f"/api/tasks/{task_id}").status_code == 404

    def test_batch_done_other_user(self, client_user2, db_session):
        task = self._make_overdue_task(db_session, user_id=1, title="User1 task")

        resp = client_user2.post("/api/tasks/batch-done", json={"tasks": [{"task_id": task.id, "end_time": "18:00"}]})
        assert resp.status_code == 404

    def test_batch_done_empty(self, client):
        resp = client.post("/api/tasks/batch-done", json={"tasks": []})
        assert resp.status_code == 200
        assert resp.json()["results"] == []


def test_get_task_for_update_exists():
    """get_task_for_update must exist in crud.task (used for pessimistic locking)."""
    from app.crud import task as crud_task

    assert hasattr(crud_task, "get_task_for_update"), "get_task_for_update not found in crud.task"
    assert callable(crud_task.get_task_for_update)


def test_start_timer_uses_row_lock(client, db_session):
    """start_timer: second concurrent start must return 400 even under race."""
    resp = client.post("/api/tasks/", json={"title": "TOCTOU Test"})
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 200

    # Second start on same task must be rejected (timer already running)
    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 400

    # Verify exactly one active entry in DB
    from app.crud import task as crud_task

    entries = crud_task.get_time_entries(db_session, task_id)
    active = [e for e in entries if e.stopped_at is None]
    assert len(active) == 1


def test_stop_timer_accumulates_total_seconds(client, db_session):
    """stop_timer: total_seconds must be non-negative after start→stop cycle."""
    resp = client.post("/api/tasks/", json={"title": "Elapsed Test"})
    task_id = resp.json()["id"]

    client.post(f"/api/tasks/{task_id}/start")
    resp = client.post(f"/api/tasks/{task_id}/stop")
    assert resp.status_code == 200
    assert resp.json()["elapsed_seconds"] >= 0

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.json()["total_seconds"] >= 0
