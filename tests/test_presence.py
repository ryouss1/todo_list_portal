from app.models.task import Task


class TestPresenceAPI:
    def test_get_my_status_default(self, client):
        resp = client.get("/api/presence/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "offline"
        assert data["user_id"] == 1

    def test_update_status(self, client):
        resp = client.put("/api/presence/status", json={"status": "available"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "available"
        assert data["user_id"] == 1

    def test_update_status_with_message(self, client):
        resp = client.put("/api/presence/status", json={"status": "away", "message": "Lunch break"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "away"
        assert data["message"] == "Lunch break"

    def test_update_status_invalid(self, client):
        resp = client.put("/api/presence/status", json={"status": "invalid_status"})
        assert resp.status_code == 422

    def test_list_all_statuses(self, client):
        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_statuses_includes_display_name(self, client):
        client.put("/api/presence/status", json={"status": "available"})
        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user1 = [s for s in data if s["user_id"] == 1]
        assert len(user1) == 1
        assert user1[0]["display_name"] == "Default User"
        assert user1[0]["status"] == "available"

    def test_status_change_creates_log(self, client):
        client.put("/api/presence/status", json={"status": "available"})
        client.put("/api/presence/status", json={"status": "away"})

        resp = client.get("/api/presence/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        statuses = [d["status"] for d in data]
        assert "available" in statuses
        assert "away" in statuses

    def test_multiple_updates_same_row(self, client):
        client.put("/api/presence/status", json={"status": "available"})
        client.put("/api/presence/status", json={"status": "break"})
        client.put("/api/presence/status", json={"status": "offline"})

        resp = client.get("/api/presence/me")
        assert resp.status_code == 200
        assert resp.json()["status"] == "offline"

    def test_update_status_meeting(self, client):
        resp = client.put("/api/presence/status", json={"status": "meeting"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "meeting"

    def test_update_status_remote(self, client):
        resp = client.put("/api/presence/status", json={"status": "remote"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "remote"

    def test_all_users_can_see_all_statuses(self, client, client_user2, db_session):
        resp = client_user2.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user_ids = [s["user_id"] for s in data]
        assert 1 in user_ids
        assert 2 in user_ids

    def test_statuses_include_active_tickets(self, client, db_session):
        # Create an in_progress task with backlog_ticket_id
        task = Task(user_id=1, title="Ticket task", status="in_progress", backlog_ticket_id="WHT-123")
        db_session.add(task)
        db_session.flush()

        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user1 = [s for s in data if s["user_id"] == 1][0]
        assert len(user1["active_tickets"]) == 1
        assert user1["active_tickets"][0]["backlog_ticket_id"] == "WHT-123"
        assert user1["active_tickets"][0]["task_title"] == "Ticket task"
        assert user1["active_tickets"][0]["task_id"] == task.id

    def test_statuses_exclude_pending_task_tickets(self, client, db_session):
        # Pending task with ticket should NOT appear
        task = Task(user_id=1, title="Pending task", status="pending", backlog_ticket_id="WHT-999")
        db_session.add(task)
        db_session.flush()

        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user1 = [s for s in data if s["user_id"] == 1][0]
        assert len(user1["active_tickets"]) == 0

    def test_statuses_exclude_task_without_ticket(self, client, db_session):
        # In-progress task without ticket should NOT appear
        task = Task(user_id=1, title="No ticket", status="in_progress")
        db_session.add(task)
        db_session.flush()

        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user1 = [s for s in data if s["user_id"] == 1][0]
        assert len(user1["active_tickets"]) == 0

    def test_statuses_multiple_active_tickets(self, client, db_session):
        task1 = Task(user_id=1, title="Task A", status="in_progress", backlog_ticket_id="WHT-100")
        task2 = Task(user_id=1, title="Task B", status="in_progress", backlog_ticket_id="WHT-200")
        db_session.add_all([task1, task2])
        db_session.flush()

        resp = client.get("/api/presence/statuses")
        assert resp.status_code == 200
        data = resp.json()
        user1 = [s for s in data if s["user_id"] == 1][0]
        assert len(user1["active_tickets"]) == 2
        ticket_ids = [t["backlog_ticket_id"] for t in user1["active_tickets"]]
        assert "WHT-100" in ticket_ids
        assert "WHT-200" in ticket_ids


def test_presence_active_task_limit_config_exists():
    """PRESENCE_ACTIVE_TASK_LIMIT must be set in app.config."""
    from app import config

    assert hasattr(config, "PRESENCE_ACTIVE_TASK_LIMIT"), "PRESENCE_ACTIVE_TASK_LIMIT missing from config"
    assert isinstance(config.PRESENCE_ACTIVE_TASK_LIMIT, int)
    assert config.PRESENCE_ACTIVE_TASK_LIMIT > 0


def test_get_in_progress_with_backlog_respects_limit(db_session):
    """get_in_progress_with_backlog must accept a limit parameter."""
    from app.crud import task as crud_task

    # Must not raise — limit parameter must exist
    result = crud_task.get_in_progress_with_backlog(db_session, limit=5)
    assert isinstance(result, list)


class TestPagination:
    def test_list_statuses_limit(self, client, db_session):
        """GET /api/presence/statuses should support limit parameter."""
        from app.models.presence import PresenceStatus
        from portal_core.core.security import hash_password
        from portal_core.models.user import User

        for i in range(3):
            u = User(
                id=100 + i,
                email=f"pag{i}@test.com",
                display_name=f"User {i}",
                password_hash=hash_password("test"),
            )
            db_session.add(u)
            db_session.flush()
            db_session.add(PresenceStatus(user_id=u.id, status="offline"))
        db_session.flush()

        resp = client.get("/api/presence/statuses?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1
