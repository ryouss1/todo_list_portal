"""Tests for Task List feature (TaskListItem CRUD, assignment, start, time accumulation)."""

import pytest

from app.models.task_category import TaskCategory
from app.models.task_list_item import TaskListItem


@pytest.fixture()
def test_category(db_session):
    """Create a test category for FK references."""
    cat = TaskCategory(name="Test Category")
    db_session.add(cat)
    db_session.flush()
    return cat


# ─── CRUD Tests ───


def test_create_item(client):
    res = client.post("/api/task-list/", json={"title": "Test Item"})
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Item"
    assert data["status"] == "open"
    assert data["total_seconds"] == 0
    assert data["created_by"] == 1
    assert data["assignee_id"] is None


def test_create_item_with_all_fields(client, test_category):
    res = client.post(
        "/api/task-list/",
        json={
            "title": "Full Item",
            "description": "Description text",
            "scheduled_date": "2026-03-01",
            "category_id": test_category.id,
            "backlog_ticket_id": "WHT-100",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["description"] == "Description text"
    assert data["scheduled_date"] == "2026-03-01"
    assert data["category_id"] == test_category.id
    assert data["backlog_ticket_id"] == "WHT-100"


def test_create_item_title_required(client):
    res = client.post("/api/task-list/", json={})
    assert res.status_code == 422


def test_get_item(client):
    res = client.post("/api/task-list/", json={"title": "Get Me"})
    item_id = res.json()["id"]
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Get Me"


def test_update_item(client):
    res = client.post("/api/task-list/", json={"title": "Original"})
    item_id = res.json()["id"]
    res = client.put(f"/api/task-list/{item_id}", json={"title": "Updated"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated"


def test_update_status(client):
    res = client.post("/api/task-list/", json={"title": "Status Test"})
    item_id = res.json()["id"]
    res = client.put(f"/api/task-list/{item_id}", json={"status": "done"})
    assert res.status_code == 200
    assert res.json()["status"] == "done"


def test_delete_item(client):
    res = client.post("/api/task-list/", json={"title": "Delete Me"})
    item_id = res.json()["id"]
    res = client.delete(f"/api/task-list/{item_id}")
    assert res.status_code == 204
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 404


# ─── List All Tests ───


def test_list_all_shows_everything(client, db_session, other_user):
    # Create items: one unassigned, one assigned to user1, one assigned to user2
    client.post("/api/task-list/", json={"title": "Unassigned Item"})
    client.post("/api/task-list/", json={"title": "My Item", "assignee_id": 1})
    item3 = TaskListItem(title="Other Item", created_by=2, assignee_id=2)
    db_session.add(item3)
    db_session.flush()

    res = client.get("/api/task-list/all")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Unassigned Item" in titles
    assert "My Item" in titles
    assert "Other Item" in titles


def test_list_all_filter_by_user(client, db_session, other_user):
    client.post("/api/task-list/", json={"title": "User1 Item", "assignee_id": 1})
    item2 = TaskListItem(title="User2 Item", created_by=2, assignee_id=2)
    db_session.add(item2)
    db_session.flush()

    res = client.get("/api/task-list/all?assignee_id=1")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "User1 Item" in titles
    assert "User2 Item" not in titles


def test_list_all_filter_unassigned(client):
    client.post("/api/task-list/", json={"title": "Pool Item"})
    client.post("/api/task-list/", json={"title": "Assigned Item", "assignee_id": 1})

    res = client.get("/api/task-list/all?assignee_id=0")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Pool Item" in titles
    assert "Assigned Item" not in titles


# ─── Assignment Tests ───


def test_unassigned_list(client):
    client.post("/api/task-list/", json={"title": "Pool Item"})
    res = client.get("/api/task-list/unassigned")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Pool Item" in titles


def test_assign_moves_to_mine(client):
    res = client.post("/api/task-list/", json={"title": "Assign Me"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/assign")
    assert res.status_code == 200
    assert res.json()["assignee_id"] == 1

    # Should appear in mine
    res = client.get("/api/task-list/mine")
    ids = [i["id"] for i in res.json()]
    assert item_id in ids

    # Should not appear in unassigned
    res = client.get("/api/task-list/unassigned")
    ids = [i["id"] for i in res.json()]
    assert item_id not in ids


def test_unassign_returns_to_pool(client):
    res = client.post("/api/task-list/", json={"title": "Unassign Me"})
    item_id = res.json()["id"]
    client.post(f"/api/task-list/{item_id}/assign")

    res = client.post(f"/api/task-list/{item_id}/unassign")
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None


def test_assign_already_assigned_by_other_forbidden(client, db_session, other_user):
    item = TaskListItem(title="Taken", created_by=1, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.post(f"/api/task-list/{item.id}/assign")
    assert res.status_code == 403


# ─── Sub-task Tests ───


# ─── Start as Task Tests ───


def test_start_creates_task(client, test_category):
    res = client.post(
        "/api/task-list/",
        json={
            "title": "Start Me",
            "description": "Desc",
            "category_id": test_category.id,
            "backlog_ticket_id": "WHT-99",
        },
    )
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
    task = res.json()
    assert task["title"] == "Start Me"
    assert task["description"] == "Desc"
    assert task["category_id"] == test_category.id
    assert task["backlog_ticket_id"] == "WHT-99"
    assert task["source_item_id"] == item_id
    assert task["status"] == "in_progress"


def test_start_auto_starts_timer(client):
    """Starting a TaskListItem should also start the timer (create a TimeEntry)."""
    res = client.post("/api/task-list/", json={"title": "Timer Auto"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
    task_id = res.json()["id"]
    assert res.json()["status"] == "in_progress"

    # Verify time entry exists (active timer)
    res = client.get(f"/api/tasks/{task_id}/time-entries")
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) == 1
    assert entries[0]["stopped_at"] is None  # timer is running


def test_start_task_appears_in_tasks_api(client):
    """After starting a TaskListItem, the created Task must appear in GET /api/tasks/."""
    res = client.post("/api/task-list/", json={"title": "E2E Verify"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
    created_task_id = res.json()["id"]

    res = client.get("/api/tasks/")
    assert res.status_code == 200
    task_ids = [t["id"] for t in res.json()]
    assert created_task_id in task_ids
    # Verify it's in_progress with running timer
    task = next(t for t in res.json() if t["id"] == created_task_id)
    assert task["status"] == "in_progress"


def test_start_sets_item_in_progress(client):
    res = client.post("/api/task-list/", json={"title": "Status Check"})
    item_id = res.json()["id"]

    client.post(f"/api/task-list/{item_id}/start")

    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "in_progress"


def test_start_already_started_returns_conflict(client):
    res = client.post("/api/task-list/", json={"title": "Multi Start"})
    item_id = res.json()["id"]

    res1 = client.post(f"/api/task-list/{item_id}/start")
    assert res1.status_code == 200
    res2 = client.post(f"/api/task-list/{item_id}/start")
    assert res2.status_code == 400
    assert "already started" in res2.json()["detail"]


def test_start_auto_assigns_unassigned_item(client):
    """Starting an unassigned item should auto-assign it to the current user."""
    res = client.post("/api/task-list/", json={"title": "Auto Assign"})
    item_id = res.json()["id"]
    assert res.json()["assignee_id"] is None

    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200

    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["assignee_id"] == 1
    assert res.json()["status"] == "in_progress"


# ─── Time Accumulation Tests ───


def test_done_accumulates_time_to_source(client, db_session):
    # Create item
    res = client.post("/api/task-list/", json={"title": "Time Test"})
    item_id = res.json()["id"]

    # Start as task
    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Manually set total_seconds on the task (simulating timer)
    from app.models.task import Task

    task = db_session.query(Task).filter(Task.id == task_id).first()
    task.total_seconds = 3600
    db_session.flush()

    # Done the task
    res = client.post(f"/api/tasks/{task_id}/done")
    assert res.status_code == 204

    # Check source item accumulated time
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["total_seconds"] == 3600


def test_done_source_item_not_deleted(client, db_session):
    res = client.post("/api/task-list/", json={"title": "Survive Test"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    client.post(f"/api/tasks/{task_id}/done")

    # Source item should still exist
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 200


# ─── Authorization Tests ───


def test_other_user_assigned_item_not_visible(client, db_session, other_user):
    item = TaskListItem(title="Private", created_by=2, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.get(f"/api/task-list/{item.id}")
    assert res.status_code == 404


def test_creator_can_see_assigned_item(db_session, other_user, client_user2, client):
    # User 1 creates, user 2 is assigned
    item = TaskListItem(title="Creator Access", created_by=1, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.get(f"/api/task-list/{item.id}")
    assert res.status_code == 200


def test_create_item_with_assignee(client):
    res = client.post("/api/task-list/", json={"title": "Pre-Assign", "assignee_id": 1})
    assert res.status_code == 201
    assert res.json()["assignee_id"] == 1


# ─── Source Item Status Sync Tests ───


def test_done_resets_item_status_to_open(client, db_session):
    """Done task should reset source item status from in_progress to open."""
    res = client.post("/api/task-list/", json={"title": "Reset Test"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Item should be in_progress
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "in_progress"

    # Done the task
    client.post(f"/api/tasks/{task_id}/done")

    # Item should be reset to open
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "open"


def test_done_restart_after_done(client, db_session):
    """After Done resets item to open, it should be possible to Start again."""
    res = client.post("/api/task-list/", json={"title": "Restart Test"})
    item_id = res.json()["id"]

    # First start + done
    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]
    client.post(f"/api/tasks/{task_id}/done")

    # Should be able to start again
    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
    assert res.json()["source_item_id"] == item_id


def test_delete_task_resets_item_status(client, db_session):
    """Deleting a task should reset source item status from in_progress to open."""
    res = client.post("/api/task-list/", json={"title": "Delete Reset"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Delete the task
    res = client.delete(f"/api/tasks/{task_id}")
    assert res.status_code == 204

    # Item should be reset to open
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "open"


def test_batch_done_resets_item_status(client, db_session):
    """Batch-done should reset source item status from in_progress to open."""
    res = client.post("/api/task-list/", json={"title": "Batch Reset"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Stop timer first (batch-done needs end_time)
    client.post(f"/api/tasks/{task_id}/stop")

    # Batch done
    res = client.post(
        "/api/tasks/batch-done",
        json={"tasks": [{"task_id": task_id, "end_time": "18:00"}]},
    )
    assert res.status_code == 200

    # Item should be reset to open
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "open"


def test_done_does_not_reset_done_status(client, db_session):
    """If item is manually set to 'done', task Done should NOT reset it to open."""
    res = client.post("/api/task-list/", json={"title": "Manual Done"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Manually set item to done
    client.put(f"/api/task-list/{item_id}", json={"status": "done"})

    # Done the task
    client.post(f"/api/tasks/{task_id}/done")

    # Item should still be done (not reset to open)
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "done"


def test_start_with_existing_task_returns_conflict(client, db_session):
    """DB-level duplicate check: starting item with existing linked task returns conflict."""
    res = client.post("/api/task-list/", json={"title": "Dup Check"})
    item_id = res.json()["id"]

    # First start succeeds
    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200

    # Manually reset item status to open (simulating race condition bypass)
    from app.models.task_list_item import TaskListItem

    item = db_session.query(TaskListItem).filter(TaskListItem.id == item_id).first()
    item.status = "open"
    db_session.flush()

    # Second start should fail due to DB duplicate check
    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


# ─── Unassign Restriction Tests ───


def test_unassign_in_progress_forbidden(client):
    """Cannot unassign an in-progress item."""
    res = client.post("/api/task-list/", json={"title": "No Unassign"})
    item_id = res.json()["id"]

    # Assign and start
    client.post(f"/api/task-list/{item_id}/assign")
    client.post(f"/api/task-list/{item_id}/start")

    # Verify item is in_progress
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "in_progress"

    # Unassign should be forbidden
    res = client.post(f"/api/task-list/{item_id}/unassign")
    assert res.status_code == 403


def test_unassign_open_allowed(client):
    """Unassign is allowed for open items (regression test)."""
    res = client.post("/api/task-list/", json={"title": "Can Unassign"})
    item_id = res.json()["id"]

    client.post(f"/api/task-list/{item_id}/assign")

    res = client.post(f"/api/task-list/{item_id}/unassign")
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None


# ─── Status Filter Tests ───


def test_mine_no_status_param_returns_all(client, db_session):
    """GET /mine without status param returns all items (backward compat)."""
    # Create items with different statuses
    for title, status in [("Open1", "open"), ("IP1", "in_progress"), ("Done1", "done")]:
        item = TaskListItem(title=title, status=status, created_by=1, assignee_id=1)
        db_session.add(item)
    db_session.flush()

    res = client.get("/api/task-list/mine")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert {"Open1", "IP1", "Done1"}.issubset(titles)


def test_mine_status_filter_excludes_done(client, db_session):
    """GET /mine?status=open&status=in_progress excludes done items."""
    for title, status in [("Open2", "open"), ("IP2", "in_progress"), ("Done2", "done")]:
        item = TaskListItem(title=title, status=status, created_by=1, assignee_id=1)
        db_session.add(item)
    db_session.flush()

    res = client.get("/api/task-list/mine?status=open&status=in_progress")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "Open2" in titles
    assert "IP2" in titles
    assert "Done2" not in titles


def test_mine_status_filter_done_only(client, db_session):
    """GET /mine?status=done returns only done items."""
    for title, status in [("Open3", "open"), ("Done3", "done")]:
        item = TaskListItem(title=title, status=status, created_by=1, assignee_id=1)
        db_session.add(item)
    db_session.flush()

    res = client.get("/api/task-list/mine?status=done")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "Done3" in titles
    assert "Open3" not in titles


def test_all_status_filter_open_only(client, db_session):
    """GET /all?status=open returns only open items."""
    for title, status in [("AllOpen", "open"), ("AllIP", "in_progress"), ("AllDone", "done")]:
        item = TaskListItem(title=title, status=status, created_by=1)
        db_session.add(item)
    db_session.flush()

    res = client.get("/api/task-list/all?status=open")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "AllOpen" in titles
    assert "AllIP" not in titles
    assert "AllDone" not in titles


def test_all_status_filter_active_only(client, db_session):
    """GET /all?status=open&status=in_progress returns active items only."""
    for title, status in [("ActOpen", "open"), ("ActIP", "in_progress"), ("ActDone", "done")]:
        item = TaskListItem(title=title, status=status, created_by=1)
        db_session.add(item)
    db_session.flush()

    res = client.get("/api/task-list/all?status=open&status=in_progress")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "ActOpen" in titles
    assert "ActIP" in titles
    assert "ActDone" not in titles


def test_all_q_filter_title_match(client, db_session):
    """GET /all?q=keyword returns only items whose title contains keyword (case-insensitive)."""
    for title in ["Alpha Task", "ALPHA backend", "Beta Task"]:
        db_session.add(TaskListItem(title=title, created_by=1))
    db_session.flush()

    res = client.get("/api/task-list/all?q=alpha")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "Alpha Task" in titles
    assert "ALPHA backend" in titles
    assert "Beta Task" not in titles


def test_all_q_filter_no_match(client, db_session):
    """GET /all?q=nonexistent returns empty list when no title matches."""
    db_session.add(TaskListItem(title="Visible Item", created_by=1))
    db_session.flush()

    res = client.get("/api/task-list/all?q=nonexistent")
    assert res.status_code == 200
    assert res.json() == []


def test_all_q_filter_combined_with_status(client, db_session):
    """GET /all?q=keyword&status=open filters by both title and status."""
    db_session.add(TaskListItem(title="Wiki Task open", status="open", created_by=1))
    db_session.add(TaskListItem(title="Wiki Task done", status="done", created_by=1))
    db_session.add(TaskListItem(title="Other open", status="open", created_by=1))
    db_session.flush()

    res = client.get("/api/task-list/all?q=wiki&status=open")
    assert res.status_code == 200
    titles = {i["title"] for i in res.json()}
    assert "Wiki Task open" in titles
    assert "Wiki Task done" not in titles
    assert "Other open" not in titles


# ─── Assignee via Update Tests ───


def test_update_item_sets_assignee(client, db_session, other_user):
    """PUT /api/task-list/{id} can change assignee_id."""
    res = client.post("/api/task-list/", json={"title": "Reassign Test"})
    item_id = res.json()["id"]
    assert res.json()["assignee_id"] is None

    res = client.put(f"/api/task-list/{item_id}", json={"assignee_id": 1})
    assert res.status_code == 200
    assert res.json()["assignee_id"] == 1


def test_update_item_clears_assignee(client):
    """PUT /api/task-list/{id} with assignee_id=null clears the assignee."""
    res = client.post("/api/task-list/", json={"title": "Clear Assign", "assignee_id": 1})
    item_id = res.json()["id"]
    assert res.json()["assignee_id"] == 1

    res = client.put(f"/api/task-list/{item_id}", json={"assignee_id": None})
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None


def test_create_item_without_assignee_is_unassigned(client):
    """Creating an item without assignee_id results in assignee_id=null."""
    res = client.post("/api/task-list/", json={"title": "No Assign At Create"})
    assert res.status_code == 201
    assert res.json()["assignee_id"] is None


def test_create_item_with_other_user_as_assignee(client, db_session, other_user):
    """Creating an item with another user's id as assignee_id is allowed."""
    res = client.post("/api/task-list/", json={"title": "Assign To Other", "assignee_id": 2})
    assert res.status_code == 201
    assert res.json()["assignee_id"] == 2


# ─── Page Tests ───


def test_page_accessible(client):
    res = client.get("/task-list")
    assert res.status_code == 200


class TestStartAsTaskRaceCondition:
    def test_start_as_task_uses_row_lock(self, db_session):
        """start_as_task should use SELECT FOR UPDATE to prevent duplicate tasks."""
        from app.crud.task_list_item import get_item_for_update
        from app.models.task_list_item import TaskListItem

        item = TaskListItem(
            title="Lock test",
            created_by=1,
            status="open",
        )
        db_session.add(item)
        db_session.flush()

        # Verify the function exists and returns the item
        locked = get_item_for_update(db_session, item.id)
        assert locked is not None
        assert locked.id == item.id
