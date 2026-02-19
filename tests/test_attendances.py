from datetime import date, datetime, timedelta, timezone

from app.models.attendance import Attendance
from app.models.attendance_break import AttendanceBreak


class TestAttendanceAPI:
    def test_status_not_clocked_in(self, client):
        resp = client.get("/api/attendances/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_clocked_in"] is False
        assert data["current_attendance"] is None

    def test_clock_in(self, client):
        resp = client.post("/api/attendances/clock-in", json={"note": "Morning"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["clock_in"] is not None
        assert data["clock_out"] is None
        assert data["note"] == "Morning"
        assert data["user_id"] == 1
        assert data["breaks"] == []

    def test_clock_in_without_note(self, client):
        resp = client.post("/api/attendances/clock-in", json={})
        assert resp.status_code == 201
        assert resp.json()["note"] is None

    def test_status_after_clock_in(self, client):
        client.post("/api/attendances/clock-in", json={})
        resp = client.get("/api/attendances/status")
        data = resp.json()
        assert data["is_clocked_in"] is True
        assert data["current_attendance"] is not None

    def test_clock_in_duplicate_rejected(self, client):
        client.post("/api/attendances/clock-in", json={})
        resp = client.post("/api/attendances/clock-in", json={})
        assert resp.status_code == 400
        assert "Already clocked in" in resp.json()["detail"]

    def test_clock_in_after_clock_out_same_day_rejected(self, client, db_session):
        """After clocking out, re-clocking in on the same day is rejected."""
        now = datetime.now(timezone.utc)
        today = now.date()
        att = Attendance(
            user_id=1,
            date=today,
            clock_in=now - timedelta(hours=8),
            clock_out=now - timedelta(minutes=5),
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post("/api/attendances/clock-in", json={})
        assert resp.status_code == 400
        assert "Already clocked in today" in resp.json()["detail"]

    def test_clock_out(self, client, db_session):
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=1),
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post("/api/attendances/clock-out", json={"note": "Leaving"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["clock_out"] is not None
        assert data["note"] == "Leaving"

    def test_clock_out_without_clock_in(self, client):
        resp = client.post("/api/attendances/clock-out", json={})
        assert resp.status_code == 400
        assert "Not clocked in" in resp.json()["detail"]

    def test_list_attendances(self, client):
        client.post("/api/attendances/clock-in", json={})
        client.post("/api/attendances/clock-out", json={})
        resp = client.get("/api/attendances/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Verify breaks field is present
        assert "breaks" in data[0]

    def test_get_attendance(self, client):
        create_resp = client.post("/api/attendances/clock-in", json={})
        att_id = create_resp.json()["id"]
        resp = client.get(f"/api/attendances/{att_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == att_id
        assert "breaks" in resp.json()

    def test_get_attendance_not_found(self, client):
        resp = client.get("/api/attendances/99999")
        assert resp.status_code == 404


class TestAttendanceManual:
    def test_create_attendance_full(self, client):
        """Manual create with all fields including breaks."""
        resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-01-15",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "13:00"}],
                "note": "Normal day",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["date"] == "2025-01-15"
        assert data["clock_in"] is not None
        assert data["clock_out"] is not None
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is not None
        assert data["note"] == "Normal day"

    def test_create_attendance_duplicate_date(self, client):
        """Duplicate date registration should be rejected."""
        client.post(
            "/api/attendances/",
            json={"date": "2025-01-16", "clock_in": "09:00", "clock_out": "18:00"},
        )
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-01-16", "clock_in": "10:00", "clock_out": "19:00"},
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_create_attendance_no_break(self, client):
        """Create without break fields."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-01-17", "clock_in": "09:00", "clock_out": "18:00"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["breaks"] == []

    def test_create_attendance_no_clock_out(self, client):
        """Create without clock_out."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-01-18", "clock_in": "09:00"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["clock_out"] is None

    def test_update_attendance(self, client):
        """Update clock_out."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-01-19", "clock_in": "09:00"},
        )
        att_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"clock_out": "18:00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["clock_out"] is not None

    def test_update_attendance_other_user(self, client, db_session, other_user):
        """Editing another user's attendance should return 404."""
        att = Attendance(
            user_id=2,
            date=date(2025, 1, 20),
            clock_in="2025-01-20T09:00:00+00:00",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.put(
            f"/api/attendances/{att.id}",
            json={"clock_out": "18:00"},
        )
        assert resp.status_code == 404

    def test_delete_attendance(self, client):
        """Delete own attendance."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-01-21", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]
        resp = client.delete(f"/api/attendances/{att_id}")
        assert resp.status_code == 204
        # Verify it's gone
        resp = client.get(f"/api/attendances/{att_id}")
        assert resp.status_code == 404

    def test_delete_attendance_other_user(self, client, db_session, other_user):
        """Deleting another user's attendance should return 404."""
        att = Attendance(
            user_id=2,
            date=date(2025, 1, 22),
            clock_in="2025-01-22T09:00:00+00:00",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.delete(f"/api/attendances/{att.id}")
        assert resp.status_code == 404

    def test_default_set_data(self, client):
        """Verify default set equivalent data (9:00-18:00, break 12:00-13:00)."""
        resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-01-23",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "13:00"}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["clock_in"] is not None
        assert data["clock_out"] is not None
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is not None


class TestAttendanceBreaks:
    """Tests for multiple break support (max 3)."""

    def test_start_break(self, client):
        """Start a break on a clocked-in attendance."""
        resp = client.post("/api/attendances/clock-in", json={})
        att_id = resp.json()["id"]
        resp = client.post(f"/api/attendances/{att_id}/break-start")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is None

    def test_end_break(self, client, db_session):
        """End an active break."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=3),
        )
        db_session.add(att)
        db_session.flush()
        brk = AttendanceBreak(
            attendance_id=att.id,
            break_start=now - timedelta(minutes=30),
        )
        db_session.add(brk)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-end")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_end"] is not None

    def test_multiple_breaks(self, client, db_session):
        """Can take up to 3 breaks."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=6),
        )
        db_session.add(att)
        db_session.flush()
        # Create 3 completed breaks via DB
        for i in range(3):
            brk = AttendanceBreak(
                attendance_id=att.id,
                break_start=now - timedelta(hours=5 - i, minutes=30),
                break_end=now - timedelta(hours=5 - i),
            )
            db_session.add(brk)
        db_session.flush()
        resp = client.get(f"/api/attendances/{att.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 3

    def test_fourth_break_rejected(self, client, db_session):
        """4th break is rejected."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=6),
        )
        db_session.add(att)
        db_session.flush()
        # Create 3 completed breaks via DB
        for i in range(3):
            brk = AttendanceBreak(
                attendance_id=att.id,
                break_start=now - timedelta(hours=5 - i, minutes=30),
                break_end=now - timedelta(hours=5 - i),
            )
            db_session.add(brk)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-start")
        assert resp.status_code == 400
        assert "Maximum 3 breaks" in resp.json()["detail"]

    def test_break_without_clock_in(self, client):
        """Cannot start break on non-existent attendance."""
        resp = client.post("/api/attendances/99999/break-start")
        assert resp.status_code == 404

    def test_break_already_active(self, client):
        """Cannot start a new break while one is already active."""
        resp = client.post("/api/attendances/clock-in", json={})
        att_id = resp.json()["id"]
        client.post(f"/api/attendances/{att_id}/break-start")
        resp = client.post(f"/api/attendances/{att_id}/break-start")
        assert resp.status_code == 400
        assert "Break already active" in resp.json()["detail"]

    def test_end_break_no_active(self, client):
        """Cannot end break when no active break."""
        resp = client.post("/api/attendances/clock-in", json={})
        att_id = resp.json()["id"]
        resp = client.post(f"/api/attendances/{att_id}/break-end")
        assert resp.status_code == 400
        assert "No active break" in resp.json()["detail"]

    def test_break_after_clock_out(self, client, db_session):
        """Cannot start break after clocking out."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=8),
            clock_out=now - timedelta(minutes=5),
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-start")
        assert resp.status_code == 400
        assert "Already clocked out" in resp.json()["detail"]

    def test_break_other_user(self, client, db_session, other_user):
        """Cannot start break on another user's attendance."""
        att = Attendance(
            user_id=2,
            date=date(2025, 3, 1),
            clock_in="2025-03-01T00:00:00+00:00",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-start")
        assert resp.status_code == 404


class TestAttendancePresets:
    """Tests for attendance presets and default-set (presets seeded by init_db at startup)."""

    def test_list_presets(self, client):
        """List all presets (seeded by seed_default_presets)."""
        resp = client.get("/api/attendance-presets/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        names = [p["name"] for p in data]
        assert "9:00-18:00" in names
        assert "8:30-17:30" in names

    def test_get_my_preset_default(self, client):
        """User with no preset set returns null."""
        resp = client.get("/api/attendances/my-preset")
        assert resp.status_code == 200
        assert resp.json()["default_preset_id"] is None

    def test_set_my_preset(self, client):
        """Set user's default preset."""
        resp = client.put("/api/attendances/my-preset", json={"default_preset_id": 2})
        assert resp.status_code == 200
        assert resp.json()["default_preset_id"] == 2
        # Verify it persists
        resp = client.get("/api/attendances/my-preset")
        assert resp.json()["default_preset_id"] == 2

    def test_set_my_preset_not_found(self, client):
        """Setting non-existent preset returns 404."""
        resp = client.put("/api/attendances/my-preset", json={"default_preset_id": 999})
        assert resp.status_code == 404

    def test_default_set_creates_today(self, client):
        """Default set creates today's attendance with all preset fields."""
        resp = client.post("/api/attendances/default-set")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == date.today().isoformat()
        assert data["clock_in"] is not None
        assert data["clock_out"] is not None
        # Break from preset (preset 1: 12:00-13:00)
        assert len(data["breaks"]) == 1
        bs_dt = datetime.fromisoformat(data["breaks"][0]["break_start"])
        be_dt = datetime.fromisoformat(data["breaks"][0]["break_end"])
        assert bs_dt.strftime("%H:%M") == "12:00"
        assert be_dt.strftime("%H:%M") == "13:00"

    def test_default_set_overwrites_existing(self, client):
        """Default set updates existing record (same id) with all preset values."""
        today_str = date.today().isoformat()
        create_resp = client.post(
            "/api/attendances/",
            json={"date": today_str, "clock_in": "10:00", "clock_out": "19:00"},
        )
        assert create_resp.status_code == 201
        old_id = create_resp.json()["id"]
        # Default set should update the same record
        resp = client.post("/api/attendances/default-set")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == old_id
        # Break from preset
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is not None

    def test_default_set_uses_user_preset(self, client):
        """Default set uses user's selected preset (not fallback to id=1)."""
        # Set user's preset to #2 (8:30-17:30)
        client.put("/api/attendances/my-preset", json={"default_preset_id": 2})
        resp = client.post("/api/attendances/default-set")
        assert resp.status_code == 200
        data = resp.json()
        # Verify it used preset #2 times (8:30, 17:30 local time)
        clock_in_dt = datetime.fromisoformat(data["clock_in"])
        clock_out_dt = datetime.fromisoformat(data["clock_out"])
        assert clock_in_dt.strftime("%H:%M") == "08:30"
        assert clock_out_dt.strftime("%H:%M") == "17:30"


class TestAttendanceInputType:
    """Tests for input_type field and admin lock."""

    def test_input_type_default_web(self, client):
        """New attendance records default to input_type='web'."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-02-01", "clock_in": "09:00", "clock_out": "18:00"},
        )
        assert resp.status_code == 201
        assert resp.json()["input_type"] == "web"

    def test_clock_in_input_type_web(self, client):
        """Clock-in records default to input_type='web'."""
        resp = client.post("/api/attendances/clock-in", json={})
        assert resp.status_code == 201
        assert resp.json()["input_type"] == "web"

    def test_admin_lock_update(self, client, db_session):
        """Cannot update an admin-entered attendance."""
        att = Attendance(
            user_id=1,
            date=date(2025, 2, 2),
            clock_in="2025-02-02T00:00:00+00:00",
            input_type="admin",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.put(f"/api/attendances/{att.id}", json={"clock_out": "18:00"})
        assert resp.status_code == 403

    def test_admin_lock_delete(self, client, db_session):
        """Cannot delete an admin-entered attendance."""
        att = Attendance(
            user_id=1,
            date=date(2025, 2, 3),
            clock_in="2025-02-03T00:00:00+00:00",
            input_type="admin",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.delete(f"/api/attendances/{att.id}")
        assert resp.status_code == 403

    def test_admin_lock_default_set(self, client, db_session):
        """Cannot overwrite admin-entered attendance via default-set."""
        att = Attendance(
            user_id=1,
            date=date.today(),
            clock_in="2025-02-04T00:00:00+00:00",
            input_type="admin",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post("/api/attendances/default-set")
        assert resp.status_code == 403

    def test_web_record_editable(self, client):
        """Web-entered records can be updated normally."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-02-05", "clock_in": "09:00"},
        )
        att_id = create_resp.json()["id"]
        resp = client.put(f"/api/attendances/{att_id}", json={"clock_out": "18:00"})
        assert resp.status_code == 200

    def test_update_attendance_with_breaks(self, client):
        """Update attendance to add breaks via edit."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-03-10", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]
        assert create_resp.json()["breaks"] == []

        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"breaks": [{"start": "12:00", "end": "13:00"}]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is not None

    def test_update_attendance_replace_breaks(self, client):
        """Updating breaks replaces all existing breaks."""
        create_resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-03-11",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "13:00"}],
            },
        )
        att_id = create_resp.json()["id"]
        assert len(create_resp.json()["breaks"]) == 1

        resp = client.put(
            f"/api/attendances/{att_id}",
            json={
                "breaks": [
                    {"start": "10:00", "end": "10:15"},
                    {"start": "15:00", "end": "15:15"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 2

    def test_update_attendance_clear_breaks(self, client):
        """Sending empty breaks list removes all breaks."""
        create_resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-03-12",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "13:00"}],
            },
        )
        att_id = create_resp.json()["id"]
        assert len(create_resp.json()["breaks"]) == 1

        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"breaks": []},
        )
        assert resp.status_code == 200
        assert resp.json()["breaks"] == []

    def test_update_attendance_breaks_max_3(self, client):
        """Only first 3 breaks are kept when more are sent."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-03-13", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/attendances/{att_id}",
            json={
                "breaks": [
                    {"start": "10:00", "end": "10:15"},
                    {"start": "12:00", "end": "13:00"},
                    {"start": "15:00", "end": "15:15"},
                    {"start": "16:00", "end": "16:15"},
                ],
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["breaks"]) == 3

    def test_update_attendance_breaks_without_end(self, client):
        """Break without end time is allowed."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-03-14", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"breaks": [{"start": "12:00"}]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breaks"]) == 1
        assert data["breaks"][0]["break_start"] is not None
        assert data["breaks"][0]["break_end"] is None

    def test_admin_lock_break_start(self, client, db_session):
        """Cannot start break on admin-entered attendance."""
        att = Attendance(
            user_id=1,
            date=date(2025, 2, 6),
            clock_in="2025-02-06T00:00:00+00:00",
            input_type="admin",
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-start")
        assert resp.status_code == 403


class TestAttendanceMonthFilter:
    """Tests for month filter and Excel export."""

    def test_list_attendances_with_month_filter(self, client):
        """Filter by year/month returns only matching records."""
        # Create records in different months
        client.post(
            "/api/attendances/",
            json={"date": "2025-04-10", "clock_in": "09:00", "clock_out": "18:00"},
        )
        client.post(
            "/api/attendances/",
            json={"date": "2025-05-10", "clock_in": "09:00", "clock_out": "18:00"},
        )
        # Filter for April
        resp = client.get("/api/attendances/?year=2025&month=4")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2025-04-10"

    def test_list_attendances_no_filter(self, client):
        """No filter returns all records (backwards compatible)."""
        client.post(
            "/api/attendances/",
            json={"date": "2025-06-01", "clock_in": "09:00", "clock_out": "18:00"},
        )
        client.post(
            "/api/attendances/",
            json={"date": "2025-07-01", "clock_in": "09:00", "clock_out": "18:00"},
        )
        resp = client.get("/api/attendances/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_export_excel(self, client):
        """Export returns xlsx with correct headers."""
        client.post(
            "/api/attendances/",
            json={"date": "2025-08-15", "clock_in": "09:00", "clock_out": "18:00"},
        )
        resp = client.get("/api/attendances/export?year=2025&month=8")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert 'filename="attendance_2025_08.xlsx"' in resp.headers["content-disposition"]
        # Verify it's valid xlsx content (non-empty)
        assert len(resp.content) > 0

    def test_export_excel_empty_month(self, client):
        """Export for a month with no data still returns 200 with valid xlsx."""
        resp = client.get("/api/attendances/export?year=2020&month=1")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert len(resp.content) > 0


class TestAttendanceMinDuration:
    """Tests for 1-minute minimum duration validation."""

    def test_create_attendance_short_duration_rejected(self, client):
        """Manual create with clock_in/clock_out < 1 minute apart is rejected."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-09-01", "clock_in": "09:00", "clock_out": "09:00"},
        )
        assert resp.status_code == 400
        assert "勤務時間" in resp.json()["detail"]
        assert "1分以上" in resp.json()["detail"]

    def test_create_attendance_exactly_one_minute_ok(self, client):
        """Manual create with exactly 1 minute duration is allowed."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-09-02", "clock_in": "09:00", "clock_out": "09:01"},
        )
        assert resp.status_code == 201

    def test_create_attendance_short_break_rejected(self, client):
        """Manual create with break < 1 minute is rejected."""
        resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-09-03",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "12:00"}],
            },
        )
        assert resp.status_code == 400
        assert "休憩時間" in resp.json()["detail"]
        assert "1分以上" in resp.json()["detail"]

    def test_create_attendance_break_one_minute_ok(self, client):
        """Manual create with exactly 1 minute break is allowed."""
        resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-09-04",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00", "end": "12:01"}],
            },
        )
        assert resp.status_code == 201

    def test_update_attendance_short_duration_rejected(self, client):
        """Updating clock_out to make duration < 1 minute is rejected."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-09-05", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"clock_out": "09:00"},
        )
        assert resp.status_code == 400
        assert "勤務時間" in resp.json()["detail"]

    def test_update_attendance_short_break_rejected(self, client):
        """Updating breaks with duration < 1 minute is rejected."""
        create_resp = client.post(
            "/api/attendances/",
            json={"date": "2025-09-06", "clock_in": "09:00", "clock_out": "18:00"},
        )
        att_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/attendances/{att_id}",
            json={"breaks": [{"start": "12:00", "end": "12:00"}]},
        )
        assert resp.status_code == 400
        assert "休憩時間" in resp.json()["detail"]

    def test_clock_out_too_soon_rejected(self, client, db_session):
        """Real-time clock out within 1 minute of clock in is rejected."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(seconds=30),  # 30 seconds ago
        )
        db_session.add(att)
        db_session.flush()
        resp = client.post("/api/attendances/clock-out", json={})
        assert resp.status_code == 400
        assert "勤務時間" in resp.json()["detail"]

    def test_end_break_too_soon_rejected(self, client, db_session):
        """Real-time break end within 1 minute of break start is rejected."""
        now = datetime.now(timezone.utc)
        att = Attendance(
            user_id=1,
            date=now.date(),
            clock_in=now - timedelta(hours=1),
        )
        db_session.add(att)
        db_session.flush()
        brk = AttendanceBreak(
            attendance_id=att.id,
            break_start=now - timedelta(seconds=30),  # 30 seconds ago
        )
        db_session.add(brk)
        db_session.flush()
        resp = client.post(f"/api/attendances/{att.id}/break-end")
        assert resp.status_code == 400
        assert "休憩時間" in resp.json()["detail"]

    def test_create_no_clock_out_skips_duration_check(self, client):
        """Manual create without clock_out does not validate duration."""
        resp = client.post(
            "/api/attendances/",
            json={"date": "2025-09-07", "clock_in": "09:00"},
        )
        assert resp.status_code == 201

    def test_break_without_end_skips_duration_check(self, client):
        """Break without end time does not validate duration."""
        resp = client.post(
            "/api/attendances/",
            json={
                "date": "2025-09-08",
                "clock_in": "09:00",
                "clock_out": "18:00",
                "breaks": [{"start": "12:00"}],
            },
        )
        assert resp.status_code == 201
