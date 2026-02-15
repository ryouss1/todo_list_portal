"""Tests for Calendar Room (facility reservation) feature."""

from datetime import datetime, timezone

from app.models.calendar_event import CalendarEvent
from app.models.calendar_room import CalendarRoom


def _seed_room(db_session, name="Test Room", capacity=10, sort_order=1):
    room = CalendarRoom(name=name, capacity=capacity, sort_order=sort_order, is_active=True)
    db_session.add(room)
    db_session.flush()
    return room


def _make_event(db_session, creator_id=1, room_id=None, **kwargs):
    defaults = {
        "title": "Test Event",
        "event_type": "meeting",
        "start_at": datetime(2026, 3, 1, 1, 0, 0, tzinfo=timezone.utc),
        "end_at": datetime(2026, 3, 1, 2, 0, 0, tzinfo=timezone.utc),
        "all_day": False,
        "visibility": "public",
    }
    defaults.update(kwargs)
    event = CalendarEvent(creator_id=creator_id, room_id=room_id, **defaults)
    db_session.add(event)
    db_session.flush()
    return event


class TestRoomCRUD:
    """Room CRUD operations (admin only)."""

    def test_list_active_rooms(self, client):
        resp = client.get("/api/calendar/rooms")
        assert resp.status_code == 200
        # Seeded rooms should be there
        names = [r["name"] for r in resp.json()]
        assert "大会議室" in names
        assert "中会議室" in names
        assert "小会議室" in names

    def test_create_room_admin(self, client):
        resp = client.post(
            "/api/calendar/rooms",
            json={
                "name": "応接室",
                "description": "1F VIP room",
                "capacity": 6,
                "sort_order": 10,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "応接室"
        assert data["capacity"] == 6
        assert data["is_active"] is True

    def test_create_room_non_admin(self, client_user2):
        resp = client_user2.post(
            "/api/calendar/rooms",
            json={
                "name": "不正な部屋",
            },
        )
        assert resp.status_code == 403

    def test_create_room_duplicate_name(self, client):
        client.post("/api/calendar/rooms", json={"name": "UniqueRoom"})
        resp = client.post("/api/calendar/rooms", json={"name": "UniqueRoom"})
        assert resp.status_code == 400  # ConflictError

    def test_update_room(self, client, db_session):
        room = _seed_room(db_session, name="Update Me")
        resp = client.put(
            f"/api/calendar/rooms/{room.id}",
            json={
                "name": "Updated Room",
                "capacity": 20,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Room"
        assert resp.json()["capacity"] == 20

    def test_delete_room_logical(self, client, db_session):
        room = _seed_room(db_session, name="Delete Me")
        resp = client.delete(f"/api/calendar/rooms/{room.id}")
        assert resp.status_code == 204
        # Should be gone from active list
        active = client.get("/api/calendar/rooms")
        names = [r["name"] for r in active.json()]
        assert "Delete Me" not in names

    def test_list_all_rooms_admin(self, client, db_session):
        room = _seed_room(db_session, name="Hidden Room")
        room.is_active = False
        db_session.flush()
        resp = client.get("/api/calendar/rooms/all")
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "Hidden Room" in names

    def test_list_all_rooms_non_admin(self, client_user2):
        resp = client_user2.get("/api/calendar/rooms/all")
        assert resp.status_code == 403


class TestRoomReservation:
    """Event creation/update with room_id and conflict detection."""

    def test_create_event_with_room(self, client, db_session):
        room = _seed_room(db_session, name="Room A")
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Meeting in Room A",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room.id,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["room_id"] == room.id
        assert data["room_name"] == "Room A"
        assert data["location"] == "Room A"  # Auto-filled

    def test_create_event_room_conflict(self, client, db_session):
        room = _seed_room(db_session, name="Room B")
        # First reservation
        client.post(
            "/api/calendar/events",
            json={
                "title": "First Meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room.id,
            },
        )
        # Overlapping reservation in same room
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Conflict Meeting",
                "start_at": "2026-03-01T10:30:00+09:00",
                "end_at": "2026-03-01T11:30:00+09:00",
                "room_id": room.id,
            },
        )
        assert resp.status_code == 400  # ConflictError
        assert "既に予約" in resp.json()["detail"]

    def test_create_event_no_conflict_different_room(self, client, db_session):
        room1 = _seed_room(db_session, name="Room C1")
        room2 = _seed_room(db_session, name="Room C2")
        client.post(
            "/api/calendar/events",
            json={
                "title": "Meeting 1",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room1.id,
            },
        )
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Meeting 2",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room2.id,
            },
        )
        assert resp.status_code == 201

    def test_create_event_no_conflict_different_time(self, client, db_session):
        room = _seed_room(db_session, name="Room D")
        client.post(
            "/api/calendar/events",
            json={
                "title": "Morning Meeting",
                "start_at": "2026-03-01T09:00:00+09:00",
                "end_at": "2026-03-01T10:00:00+09:00",
                "room_id": room.id,
            },
        )
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "Afternoon Meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room.id,
            },
        )
        assert resp.status_code == 201  # Back-to-back is fine (10:00 not < 10:00)

    def test_update_event_room_conflict(self, client, db_session):
        room = _seed_room(db_session, name="Room E")
        # Existing reservation
        _make_event(
            db_session,
            creator_id=1,
            room_id=room.id,
            title="Existing",
            start_at=datetime(2026, 3, 1, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 1, 2, 0, 0, tzinfo=timezone.utc),
        )
        # Create a second event (no room)
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "Move Me",
                "start_at": "2026-03-01T14:00:00+09:00",
                "end_at": "2026-03-01T15:00:00+09:00",
            },
        )
        event_id = create.json()["id"]
        # Try to assign the same room at overlapping time
        resp = client.put(
            f"/api/calendar/events/{event_id}",
            json={
                "room_id": room.id,
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
            },
        )
        assert resp.status_code == 400
        assert "既に予約" in resp.json()["detail"]

    def test_update_own_event_no_self_conflict(self, client, db_session):
        room = _seed_room(db_session, name="Room F")
        create = client.post(
            "/api/calendar/events",
            json={
                "title": "My Meeting",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
                "room_id": room.id,
            },
        )
        event_id = create.json()["id"]
        # Update same event (should not conflict with itself)
        resp = client.put(
            f"/api/calendar/events/{event_id}",
            json={
                "title": "Updated Title",
            },
        )
        assert resp.status_code == 200

    def test_event_without_room(self, client):
        resp = client.post(
            "/api/calendar/events",
            json={
                "title": "No Room Event",
                "start_at": "2026-03-01T10:00:00+09:00",
                "end_at": "2026-03-01T11:00:00+09:00",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["room_id"] is None
        assert resp.json()["room_name"] is None


class TestRoomAvailability:
    """Room availability endpoint."""

    def test_get_availability(self, client, db_session):
        room = _seed_room(db_session, name="Room G")
        _make_event(
            db_session,
            creator_id=1,
            room_id=room.id,
            title="Morning",
            start_at=datetime(2026, 3, 1, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 1, 2, 0, 0, tzinfo=timezone.utc),
        )
        resp = client.get(
            f"/api/calendar/rooms/{room.id}/availability",
            params={
                "date": "2026-03-01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["room_id"] == room.id
        assert data["room_name"] == "Room G"
        assert len(data["reservations"]) == 1
        assert data["reservations"][0]["title"] == "Morning"

    def test_get_availability_empty(self, client, db_session):
        room = _seed_room(db_session, name="Room H")
        resp = client.get(
            f"/api/calendar/rooms/{room.id}/availability",
            params={
                "date": "2026-03-01",
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["reservations"]) == 0

    def test_get_availability_not_found(self, client):
        resp = client.get(
            "/api/calendar/rooms/99999/availability",
            params={
                "date": "2026-03-01",
            },
        )
        assert resp.status_code == 404
