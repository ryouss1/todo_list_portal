"""Tests for data isolation between users (ISSUE-007)."""

from datetime import datetime, timezone

from app.models.attendance import Attendance
from app.models.task import Task
from app.models.todo import Todo


class TestTodoAuthorization:
    def _create_todo_for_user1(self, db_session):
        todo = Todo(user_id=1, title="User1 Todo", priority=0, is_completed=False)
        db_session.add(todo)
        db_session.flush()
        return todo.id

    def test_get_other_user_todo(self, client_user2, db_session):
        todo_id = self._create_todo_for_user1(db_session)
        res = client_user2.get(f"/api/todos/{todo_id}")
        assert res.status_code == 404

    def test_update_other_user_todo(self, client_user2, db_session):
        todo_id = self._create_todo_for_user1(db_session)
        res = client_user2.put(f"/api/todos/{todo_id}", json={"title": "Hacked"})
        assert res.status_code == 404

    def test_delete_other_user_todo(self, client_user2, db_session):
        todo_id = self._create_todo_for_user1(db_session)
        res = client_user2.delete(f"/api/todos/{todo_id}")
        assert res.status_code == 404

    def test_toggle_other_user_todo(self, client_user2, db_session):
        todo_id = self._create_todo_for_user1(db_session)
        res = client_user2.patch(f"/api/todos/{todo_id}/toggle")
        assert res.status_code == 404

    def test_public_todo_visible_to_other_user(self, client_user2, db_session):
        todo = Todo(user_id=1, title="Public by user1", priority=0, is_completed=False, visibility="public")
        db_session.add(todo)
        db_session.flush()

        res = client_user2.get("/api/todos/public")
        assert res.status_code == 200
        titles = [t["title"] for t in res.json()]
        assert "Public by user1" in titles

    def test_private_todo_not_in_public_list(self, client_user2, db_session):
        todo = Todo(user_id=1, title="Private by user1", priority=0, is_completed=False, visibility="private")
        db_session.add(todo)
        db_session.flush()

        res = client_user2.get("/api/todos/public")
        assert res.status_code == 200
        titles = [t["title"] for t in res.json()]
        assert "Private by user1" not in titles

    def test_cannot_modify_other_user_public_todo(self, client_user2, db_session):
        todo = Todo(user_id=1, title="Public todo", priority=0, is_completed=False, visibility="public")
        db_session.add(todo)
        db_session.flush()

        res = client_user2.put(f"/api/todos/{todo.id}", json={"title": "Hacked"})
        assert res.status_code == 404


class TestTaskAuthorization:
    def _create_task_for_user1(self, db_session):
        task = Task(user_id=1, title="User1 Task", status="pending", total_seconds=0)
        db_session.add(task)
        db_session.flush()
        return task.id

    def test_get_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.get(f"/api/tasks/{task_id}")
        assert res.status_code == 404

    def test_update_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.put(f"/api/tasks/{task_id}", json={"title": "Hacked"})
        assert res.status_code == 404

    def test_delete_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.delete(f"/api/tasks/{task_id}")
        assert res.status_code == 404

    def test_start_timer_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.post(f"/api/tasks/{task_id}/start")
        assert res.status_code == 404

    def test_stop_timer_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.post(f"/api/tasks/{task_id}/stop")
        assert res.status_code == 404

    def test_time_entries_other_user_task(self, client_user2, db_session):
        task_id = self._create_task_for_user1(db_session)
        res = client_user2.get(f"/api/tasks/{task_id}/time-entries")
        assert res.status_code == 404


class TestAttendanceAuthorization:
    def test_get_other_user_attendance(self, client_user2, db_session):
        att = Attendance(user_id=1, clock_in=datetime.now(timezone.utc), date=datetime.now(timezone.utc).date())
        db_session.add(att)
        db_session.flush()
        res = client_user2.get(f"/api/attendances/{att.id}")
        assert res.status_code == 404
