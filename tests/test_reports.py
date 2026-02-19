from app.models.daily_report import DailyReport
from app.models.task_category import TaskCategory


def _ensure_category(db_session, category_id=7, name="その他"):
    """Ensure a task category exists for tests."""
    cat = db_session.query(TaskCategory).filter(TaskCategory.id == category_id).first()
    if not cat:
        cat = TaskCategory(id=category_id, name=name)
        db_session.add(cat)
        db_session.flush()
    return cat


class TestReportAPI:
    def test_list_reports_empty(self, client):
        resp = client.get("/api/reports/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_report(self, client, db_session):
        _ensure_category(db_session)
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Test task",
                "time_minutes": 60,
                "work_content": "Implemented new features",
                "achievements": "Completed Phase 1",
                "issues": "None",
                "next_plan": "Phase 2",
                "remarks": "Good progress",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_date"] == "2026-02-10"
        assert data["work_content"] == "Implemented new features"
        assert data["achievements"] == "Completed Phase 1"
        assert data["user_id"] == 1
        assert data["category_id"] == 7
        assert data["task_name"] == "Test task"
        assert data["time_minutes"] == 60

    def test_create_report_minimal(self, client, db_session):
        _ensure_category(db_session)
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Minimal task",
                "work_content": "Daily work",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["work_content"] == "Daily work"
        assert data["achievements"] is None
        assert data["issues"] is None
        assert data["time_minutes"] == 0

    def test_create_report_missing_required(self, client):
        resp = client.post("/api/reports/", json={"report_date": "2026-02-10"})
        assert resp.status_code == 422

    def test_create_report_missing_category(self, client):
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "task_name": "Test",
                "work_content": "Test",
            },
        )
        assert resp.status_code == 422

    def test_create_report_missing_task_name(self, client, db_session):
        _ensure_category(db_session)
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "work_content": "Test",
            },
        )
        assert resp.status_code == 422

    def test_create_report_with_time(self, client, db_session):
        _ensure_category(db_session)
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Timed task",
                "time_minutes": 120,
                "work_content": "Work",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["time_minutes"] == 120

    def test_create_report_with_backlog_ticket(self, client, db_session):
        _ensure_category(db_session)
        resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Ticket task",
                "work_content": "Work with ticket",
                "backlog_ticket_id": "WHT-123",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["backlog_ticket_id"] == "WHT-123"

    def test_update_report_backlog_ticket(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Task",
                "work_content": "Work",
            },
        )
        report_id = create_resp.json()["id"]
        assert create_resp.json()["backlog_ticket_id"] is None

        resp = client.put(
            f"/api/reports/{report_id}",
            json={"backlog_ticket_id": "WHT-456"},
        )
        assert resp.status_code == 200
        assert resp.json()["backlog_ticket_id"] == "WHT-456"

    def test_create_multiple_reports_same_date(self, client, db_session):
        _ensure_category(db_session)
        resp1 = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Task 1",
                "work_content": "First",
            },
        )
        assert resp1.status_code == 201
        resp2 = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Task 2",
                "work_content": "Second",
            },
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] != resp1.json()["id"]

    def test_get_report(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Get test",
                "work_content": "Test",
            },
        )
        report_id = create_resp.json()["id"]

        resp = client.get(f"/api/reports/{report_id}")
        assert resp.status_code == 200
        assert resp.json()["work_content"] == "Test"
        assert resp.json()["task_name"] == "Get test"

    def test_update_report(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Old task",
                "work_content": "Old",
            },
        )
        report_id = create_resp.json()["id"]

        resp = client.put(f"/api/reports/{report_id}", json={"work_content": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["work_content"] == "Updated"

    def test_update_report_category(self, client, db_session):
        _ensure_category(db_session)
        cat2 = _ensure_category(db_session, category_id=1, name="開発")
        create_resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Task",
                "work_content": "Work",
            },
        )
        report_id = create_resp.json()["id"]

        resp = client.put(f"/api/reports/{report_id}", json={"category_id": cat2.id, "task_name": "Updated task"})
        assert resp.status_code == 200
        assert resp.json()["category_id"] == cat2.id
        assert resp.json()["task_name"] == "Updated task"

    def test_delete_report(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Delete me",
                "work_content": "Delete me",
            },
        )
        report_id = create_resp.json()["id"]

        resp = client.delete(f"/api/reports/{report_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/reports/{report_id}")
        assert resp.status_code == 404

    def test_list_all_reports(self, client, db_session):
        _ensure_category(db_session)
        client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-10",
                "category_id": 7,
                "task_name": "Task 1",
                "work_content": "Report 1",
            },
        )
        client.post(
            "/api/reports/",
            json={
                "report_date": "2026-02-11",
                "category_id": 7,
                "task_name": "Task 2",
                "work_content": "Report 2",
            },
        )

        resp = client.get("/api/reports/all")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_done_task_inherits_backlog_ticket(self, client, db_session):
        _ensure_category(db_session)
        create_resp = client.post(
            "/api/tasks/",
            json={
                "title": "Ticket task",
                "report": True,
                "backlog_ticket_id": "WHT-789",
            },
        )
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/tasks/{task_id}/done")
        assert resp.status_code == 200
        data = resp.json()
        assert data["backlog_ticket_id"] == "WHT-789"


class TestReportAuthorization:
    def _create_report_for_user1(self, db_session):
        _ensure_category(db_session)
        report = DailyReport(
            user_id=1,
            report_date="2026-02-10",
            category_id=7,
            task_name="User1 task",
            time_minutes=30,
            work_content="User1 report",
        )
        db_session.add(report)
        db_session.flush()
        return report.id

    def test_other_user_can_read_report(self, client_user2, db_session):
        report_id = self._create_report_for_user1(db_session)
        resp = client_user2.get(f"/api/reports/{report_id}")
        assert resp.status_code == 200
        assert resp.json()["work_content"] == "User1 report"

    def test_cannot_update_other_user_report(self, client_user2, db_session):
        report_id = self._create_report_for_user1(db_session)
        resp = client_user2.put(f"/api/reports/{report_id}", json={"work_content": "Hacked"})
        assert resp.status_code == 404

    def test_cannot_delete_other_user_report(self, client_user2, db_session):
        report_id = self._create_report_for_user1(db_session)
        resp = client_user2.delete(f"/api/reports/{report_id}")
        assert resp.status_code == 404

    def test_other_user_sees_in_all_list(self, client_user2, db_session):
        self._create_report_for_user1(db_session)
        resp = client_user2.get("/api/reports/all")
        assert resp.status_code == 200
        contents = [r["work_content"] for r in resp.json()]
        assert "User1 report" in contents
