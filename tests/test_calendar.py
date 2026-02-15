"""Tests for Calendar feature (Phase 10)."""

from datetime import datetime, timezone

from app.models.calendar_event import CalendarEvent
from app.models.calendar_event_attendee import CalendarEventAttendee


def _make_event(db_session, creator_id=1, **kwargs):
    """Create a CalendarEvent directly in the DB session."""
    defaults = {
        "title": "Test Event",
        "event_type": "other",
        "start_at": datetime(2026, 3, 1, 1, 0, 0, tzinfo=timezone.utc),
        "all_day": False,
        "visibility": "public",
    }
    defaults.update(kwargs)
    event = CalendarEvent(creator_id=creator_id, **defaults)
    db_session.add(event)
    db_session.flush()
    return event


class TestCalendarEventCRUD:
    """Basic event create, read, update, delete."""

    def test_create_event(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Team Meeting",
                "event_type": "meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "location": "Room A",
                "visibility": "public",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Team Meeting"
        assert data["event_type"] == "meeting"
        assert data["location"] == "Room A"
        assert data["creator_id"] == 1

    def test_create_all_day_event(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Holiday",
                "start_at": "2026-03-15T00:00:00+09:00",
                "all_day": True,
                "event_type": "out_of_office",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["all_day"] is True

    def test_get_event(self, client):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Get Test",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        resp = client.get(f"/api/calendar/events/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Test"

    def test_get_event_not_found(self, client):
        resp = client.get("/api/calendar/events/99999")
        assert resp.status_code == 404

    def test_update_event(self, client):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Original",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        resp = client.put(
            f"/api/calendar/events/{event_id}",
            json={
                "title": "Updated",
                "location": "Room B",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["location"] == "Room B"

    def test_update_event_forbidden(self, db_session, client_user2):
        # Create event as user 1 directly via DB (shared-app override issue)
        event = _make_event(db_session, creator_id=1, title="User1 Event")
        resp = client_user2.put(
            f"/api/calendar/events/{event.id}",
            json={
                "title": "Hacked",
            },
        )
        assert resp.status_code == 403

    def test_delete_event(self, client):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "To Delete",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        resp = client.delete(f"/api/calendar/events/{event_id}")
        assert resp.status_code == 204
        # Confirm gone
        resp2 = client.get(f"/api/calendar/events/{event_id}")
        assert resp2.status_code == 404

    def test_delete_event_forbidden(self, db_session, client_user2):
        # Create event as user 1 directly via DB
        event = _make_event(db_session, creator_id=1, title="User1 Event")
        resp = client_user2.delete(f"/api/calendar/events/{event.id}")
        assert resp.status_code == 403

    def test_list_events_in_range(self, client):
        # Create events in March
        client.post(
            "/api/calendar/events",
            json={
                "title": "March Event",
                "start_at": "2026-03-15T10:00:00+09:00",
                "end_at": "2026-03-15T11:00:00+09:00",
            },
        )
        # Create event outside range
        client.post(
            "/api/calendar/events",
            json={
                "title": "April Event",
                "start_at": "2026-04-15T10:00:00+09:00",
            },
        )
        resp = client.get(
            "/api/calendar/events",
            params={
                "start": "2026-03-01T00:00:00+09:00",
                "end": "2026-04-01T00:00:00+09:00",
            },
        )
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json()]
        assert "March Event" in titles
        assert "April Event" not in titles

    def test_list_events_filter_by_user(self, db_session, client_user2):
        # Create events as different users via DB
        _make_event(
            db_session,
            creator_id=1,
            title="User1 Event",
            start_at=datetime(2026, 3, 10, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 10, 2, 0, 0, tzinfo=timezone.utc),
        )
        _make_event(
            db_session,
            creator_id=2,
            title="User2 Event",
            start_at=datetime(2026, 3, 10, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 10, 2, 0, 0, tzinfo=timezone.utc),
        )
        # Filter for user 2 only
        resp = client_user2.get(
            "/api/calendar/events",
            params={
                "start": "2026-03-01T00:00:00+09:00",
                "end": "2026-04-01T00:00:00+09:00",
                "user_ids": "2",
            },
        )
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json()]
        assert "User2 Event" in titles
        assert "User1 Event" not in titles


class TestCalendarPrivateEvents:
    """Private event visibility."""

    def test_private_event_masked_for_others(self, db_session, client_user2):
        # Create private event as user 1 via DB
        event = _make_event(
            db_session,
            creator_id=1,
            title="Secret Meeting",
            start_at=datetime(2026, 3, 1, 5, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 1, 6, 0, 0, tzinfo=timezone.utc),
            visibility="private",
        )
        # Other user (user_id=2) sees masked
        resp_other = client_user2.get(f"/api/calendar/events/{event.id}")
        assert resp_other.json()["title"] == "予定あり"
        assert resp_other.json()["description"] is None

    def test_private_event_in_list_masked(self, db_session, client_user2):
        _make_event(
            db_session,
            creator_id=1,
            title="Private Event",
            start_at=datetime(2026, 5, 1, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 5, 1, 2, 0, 0, tzinfo=timezone.utc),
            visibility="private",
        )
        resp = client_user2.get(
            "/api/calendar/events",
            params={
                "start": "2026-05-01T00:00:00+09:00",
                "end": "2026-06-01T00:00:00+09:00",
            },
        )
        titles = [e["title"] for e in resp.json()]
        assert "予定あり" in titles
        assert "Private Event" not in titles


class TestCalendarAttendees:
    """Attendee management."""

    def test_add_attendees_on_create(self, client, other_user):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Team Sync",
                "start_at": "2026-03-01T10:00:00+09:00",
                "attendee_ids": [2],
            },
        )
        assert resp.status_code == 201
        attendees = resp.json()["attendees"]
        user_ids = [a["user_id"] for a in attendees]
        assert 1 in user_ids  # Creator auto-added
        assert 2 in user_ids

    def test_add_attendees_after_create(self, client, other_user):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        resp = client.post(
            f"/api/calendar/events/{event_id}/attendees",
            json={
                "user_ids": [2],
            },
        )
        assert resp.status_code == 200
        user_ids = [a["user_id"] for a in resp.json()]
        assert 2 in user_ids

    def test_remove_attendee(self, client, other_user):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
                "attendee_ids": [2],
            },
        )
        event_id = create.json()["id"]
        resp = client.delete(f"/api/calendar/events/{event_id}/attendees/2")
        assert resp.status_code == 204

    def test_respond_to_event(self, db_session, client_user2):
        # Create event as user 1 and add user 2 as attendee via DB
        event = _make_event(db_session, creator_id=1, title="Meeting")
        db_session.add(CalendarEventAttendee(event_id=event.id, user_id=2, response_status="pending"))
        db_session.flush()
        resp = client_user2.patch(
            f"/api/calendar/events/{event.id}/respond",
            json={
                "response_status": "accepted",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["response_status"] == "accepted"

    def test_respond_not_attendee(self, db_session, client_user2):
        # Create event as user 1, user 2 is NOT an attendee
        event = _make_event(db_session, creator_id=1, title="Exclusive Meeting")
        resp = client_user2.patch(
            f"/api/calendar/events/{event.id}/respond",
            json={
                "response_status": "declined",
            },
        )
        assert resp.status_code == 404

    def test_only_creator_can_add_attendees(self, db_session, client_user2):
        # Create event as user 1 via DB
        event = _make_event(db_session, creator_id=1, title="Meeting")
        resp = client_user2.post(
            f"/api/calendar/events/{event.id}/attendees",
            json={
                "user_ids": [2],
            },
        )
        assert resp.status_code == 403


class TestCalendarReminders:
    """Reminder CRUD."""

    def test_set_reminder_on_create(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Reminded Event",
                "start_at": "2026-03-01T10:00:00+09:00",
                "reminder_minutes": 15,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["my_reminder_minutes"] == 15

    def test_set_reminder_after_create(self, client):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Event",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        resp = client.put(
            f"/api/calendar/events/{event_id}/reminder",
            json={
                "minutes_before": 30,
            },
        )
        assert resp.status_code == 204

        # Verify
        detail = client.get(f"/api/calendar/events/{event_id}")
        assert detail.json()["my_reminder_minutes"] == 30

    def test_delete_reminder(self, client):
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Event",
                "start_at": "2026-03-01T10:00:00+09:00",
                "reminder_minutes": 10,
            },
        )
        event_id = create.json()["id"]
        resp = client.delete(f"/api/calendar/events/{event_id}/reminder")
        assert resp.status_code == 204

        detail = client.get(f"/api/calendar/events/{event_id}")
        assert detail.json()["my_reminder_minutes"] is None


class TestCalendarRecurrence:
    """Recurring events."""

    def test_create_recurring_weekly(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Weekly Standup",
                "start_at": "2026-03-02T09:00:00+09:00",
                "end_at": "2026-03-02T09:30:00+09:00",
                "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO"

    def test_recurring_events_expand_in_range(self, client):
        client.post(
            "/api/calendar/events",
            json={
                "title": "Daily Standup",
                "start_at": "2026-06-01T09:00:00+00:00",
                "end_at": "2026-06-01T09:30:00+00:00",
                "recurrence_rule": "FREQ=DAILY",
                "recurrence_end": "2026-06-30",
            },
        )
        # Query for 1 week
        resp = client.get(
            "/api/calendar/events",
            params={
                "start": "2026-06-01T00:00:00+00:00",
                "end": "2026-06-08T00:00:00+00:00",
                "include_source": "false",
            },
        )
        assert resp.status_code == 200
        standup_events = [e for e in resp.json() if e["title"] == "Daily Standup"]
        assert len(standup_events) >= 7  # 7 days


class TestCalendarSettings:
    """User calendar settings."""

    def test_get_default_settings(self, client):
        resp = client.get("/api/calendar/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_view"] == "dayGridMonth"
        assert data["default_color"] == "#3788d8"
        assert data["show_task_list"] is True

    def test_update_settings(self, client):
        resp = client.put(
            "/api/calendar/settings",
            json={
                "default_view": "timeGridWeek",
                "default_color": "#e74c3c",
                "show_reports": True,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["default_view"] == "timeGridWeek"
        assert resp.json()["default_color"] == "#e74c3c"
        assert resp.json()["show_reports"] is True

    def test_invalid_color_rejected(self, client):
        resp = client.put(
            "/api/calendar/settings",
            json={
                "default_color": "red",
            },
        )
        assert resp.status_code == 422


class TestCalendarColorValidation:
    """Color field validation."""

    def test_valid_color(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Colored Event",
                "start_at": "2026-03-01T10:00:00+09:00",
                "color": "#ff0000",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["color"] == "#ff0000"

    def test_invalid_color_rejected(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Bad Color",
                "start_at": "2026-03-01T10:00:00+09:00",
                "color": "red",
            },
        )
        assert resp.status_code == 422

    def test_null_color_uses_default(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Default Color",
                "start_at": "2026-03-01T10:00:00+09:00",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["color"] is None  # Uses user default at display time
