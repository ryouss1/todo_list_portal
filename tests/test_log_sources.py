"""Tests for log source CRUD API."""


class TestLogSourceCRUD:
    def test_create_source(self, client):
        res = client.post(
            "/api/log-sources/",
            json={
                "name": "App Log",
                "file_path": "/var/log/app.log",
                "system_name": "app-server",
                "log_type": "application",
                "polling_interval_sec": 30,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "App Log"
        assert data["file_path"] == "/var/log/app.log"
        assert data["system_name"] == "app-server"
        assert data["is_enabled"] is True
        assert data["default_severity"] == "INFO"
        assert data["last_read_position"] == 0

    def test_create_source_invalid_regex(self, client):
        res = client.post(
            "/api/log-sources/",
            json={
                "name": "Bad Regex",
                "file_path": "/var/log/bad.log",
                "system_name": "test",
                "log_type": "test",
                "parser_pattern": "[invalid(regex",
            },
        )
        assert res.status_code == 422

    def test_create_source_low_interval(self, client):
        res = client.post(
            "/api/log-sources/",
            json={
                "name": "Too Fast",
                "file_path": "/var/log/fast.log",
                "system_name": "test",
                "log_type": "test",
                "polling_interval_sec": 2,
            },
        )
        assert res.status_code == 422

    def test_list_sources(self, client):
        client.post(
            "/api/log-sources/",
            json={
                "name": "Source 1",
                "file_path": "/var/log/s1.log",
                "system_name": "sys1",
                "log_type": "app",
            },
        )
        client.post(
            "/api/log-sources/",
            json={
                "name": "Source 2",
                "file_path": "/var/log/s2.log",
                "system_name": "sys2",
                "log_type": "app",
            },
        )
        res = client.get("/api/log-sources/")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2

    def test_get_source(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json={
                "name": "Get Me",
                "file_path": "/var/log/get.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        source_id = create_res.json()["id"]
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Get Me"

    def test_get_source_not_found(self, client):
        res = client.get("/api/log-sources/99999")
        assert res.status_code == 404

    def test_update_source(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json={
                "name": "Original",
                "file_path": "/var/log/orig.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"name": "Updated"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_delete_source(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json={
                "name": "Delete Me",
                "file_path": "/var/log/del.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        source_id = create_res.json()["id"]
        res = client.delete(f"/api/log-sources/{source_id}")
        assert res.status_code == 204
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.status_code == 404

    def test_toggle_enable(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json={
                "name": "Toggle Me",
                "file_path": "/var/log/toggle.log",
                "system_name": "test",
                "log_type": "test",
                "is_enabled": True,
            },
        )
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"is_enabled": False})
        assert res.status_code == 200
        assert res.json()["is_enabled"] is False
        res = client.put(f"/api/log-sources/{source_id}", json={"is_enabled": True})
        assert res.status_code == 200
        assert res.json()["is_enabled"] is True


class TestLogSourcePathValidation:
    """ISSUE-021+034: Path traversal prevention tests."""

    def test_relative_path_rejected(self, client):
        res = client.post(
            "/api/log-sources/",
            json={
                "name": "Relative",
                "file_path": "var/log/app.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        assert res.status_code == 422

    def test_path_traversal_rejected(self, client):
        res = client.post(
            "/api/log-sources/",
            json={
                "name": "Traversal",
                "file_path": "/var/log/../../etc/passwd",
                "system_name": "test",
                "log_type": "test",
            },
        )
        assert res.status_code == 422

    def test_update_path_traversal_rejected(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json={
                "name": "Valid Source",
                "file_path": "/var/log/app.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        source_id = create_res.json()["id"]
        res = client.put(
            f"/api/log-sources/{source_id}",
            json={"file_path": "/tmp/../etc/shadow"},
        )
        assert res.status_code == 422


class TestLogSourceRBAC:
    """ISSUE-033: Authorization tests for log source management."""

    def test_non_admin_cannot_create_source(self, client_user2):
        res = client_user2.post(
            "/api/log-sources/",
            json={
                "name": "Unauthorized",
                "file_path": "/var/log/test.log",
                "system_name": "test",
                "log_type": "test",
            },
        )
        assert res.status_code == 403

    def test_non_admin_cannot_update_source(self, client_user2, db_session):
        from app.models.log_source import LogSource

        source = LogSource(
            name="Admin Source",
            file_path="/var/log/admin.log",
            system_name="test",
            log_type="test",
        )
        db_session.add(source)
        db_session.flush()
        res = client_user2.put(f"/api/log-sources/{source.id}", json={"name": "Hacked"})
        assert res.status_code == 403

    def test_non_admin_cannot_delete_source(self, client_user2, db_session):
        from app.models.log_source import LogSource

        source = LogSource(
            name="Protected",
            file_path="/var/log/protected.log",
            system_name="test",
            log_type="test",
        )
        db_session.add(source)
        db_session.flush()
        res = client_user2.delete(f"/api/log-sources/{source.id}")
        assert res.status_code == 403

    def test_non_admin_can_read_sources(self, client_user2, db_session):
        """Non-admin users can read log source list and details."""
        from app.models.log_source import LogSource

        source = LogSource(
            name="Readable",
            file_path="/var/log/readable.log",
            system_name="test",
            log_type="test",
        )
        db_session.add(source)
        db_session.flush()
        res = client_user2.get("/api/log-sources/")
        assert res.status_code == 200
