"""Tests for log source CRUD API (v2 with remote connections + multi-path)."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.log_entry import LogEntry
from app.models.log_file import LogFile
from app.models.log_source import LogSource
from app.models.log_source_path import LogSourcePath
from app.services.remote_connector import RemoteFileInfo

# Module-level variable to hold the test department ID.
# Set by the _setup_test_department autouse fixture.
_test_dept_id: int = 1


@pytest.fixture(autouse=True)
def _setup_test_department(db_session):
    """Create a department in the test transaction and expose its ID module-wide."""
    global _test_dept_id
    from portal_core.models.department import Department

    dept = Department(name="Log Source Test Dept", sort_order=0, is_active=True)
    db_session.add(dept)
    db_session.flush()
    _test_dept_id = dept.id
    yield
    # No teardown needed — transaction rolls back after each test


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set encryption key for all log source tests."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setattr("portal_core.core.encryption.CREDENTIAL_ENCRYPTION_KEY", key)
    monkeypatch.setattr("portal_core.core.encryption._fernet", None)  # Reset cached fernet


def _valid_create_payload(**overrides) -> dict:
    """Return a valid log source create payload with optional overrides."""
    data = {
        "name": "App Log",
        "department_id": _test_dept_id,
        "access_method": "ftp",
        "host": "192.168.1.100",
        "username": "loguser",
        "password": "secret123",
        "paths": [{"base_path": "/var/log/app", "file_pattern": "*.log"}],
        "source_type": "WEB",
        "collection_mode": "metadata_only",
    }
    data.update(overrides)
    return data


def _create_source_in_db(db_session, **overrides) -> LogSource:
    """Insert a LogSource + LogSourcePath directly into the DB with encrypted credentials."""
    from app.core.encryption import encrypt_value

    defaults = {
        "name": "DB Source",
        "department_id": _test_dept_id,
        "access_method": "ftp",
        "host": "10.0.0.1",
        "username": encrypt_value("dbuser"),
        "password": encrypt_value("dbpass"),
        "encoding": "utf-8",
        "source_type": "OTHER",
        "collection_mode": "metadata_only",
        "default_severity": "INFO",
        "polling_interval_sec": 60,
        "is_enabled": True,
        "consecutive_errors": 0,
    }
    # Extract path overrides
    path_data = overrides.pop("paths", None)

    defaults.update(overrides)
    source = LogSource(**defaults)
    db_session.add(source)
    db_session.flush()

    # Create default path(s)
    if path_data:
        for p in path_data:
            path = LogSourcePath(
                source_id=source.id,
                base_path=p.get("base_path", "/logs"),
                file_pattern=p.get("file_pattern", "*.log"),
                is_enabled=p.get("is_enabled", True),
            )
            db_session.add(path)
    else:
        path = LogSourcePath(
            source_id=source.id,
            base_path="/logs",
            file_pattern="*.log",
            is_enabled=True,
        )
        db_session.add(path)
    db_session.flush()
    return source


# ---- Response field checklist ----
EXPECTED_RESPONSE_FIELDS = {
    "id",
    "name",
    "department_id",
    "department_name",
    "access_method",
    "host",
    "port",
    "username_masked",
    "domain",
    "paths",
    "encoding",
    "source_type",
    "polling_interval_sec",
    "collection_mode",
    "parser_pattern",
    "severity_field",
    "default_severity",
    "is_enabled",
    "alert_on_change",
    "consecutive_errors",
    "last_checked_at",
    "last_error",
    "created_at",
    "updated_at",
}


class TestLogSourceCRUD:
    """CRUD operations for log sources."""

    def test_create_source(self, client):
        res = client.post("/api/log-sources/", json=_valid_create_payload())
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "App Log"
        assert data["department_id"] == _test_dept_id
        assert data["access_method"] == "ftp"
        assert data["host"] == "192.168.1.100"
        assert data["source_type"] == "WEB"
        assert data["collection_mode"] == "metadata_only"
        assert data["encoding"] == "utf-8"
        assert data["is_enabled"] is True
        assert data["default_severity"] == "INFO"
        assert data["polling_interval_sec"] == 60
        assert data["consecutive_errors"] == 0
        assert data["last_checked_at"] is None
        assert data["last_error"] is None
        # Check paths
        assert len(data["paths"]) == 1
        assert data["paths"][0]["base_path"] == "/var/log/app"
        assert data["paths"][0]["file_pattern"] == "*.log"
        assert data["paths"][0]["is_enabled"] is True
        # Ensure all expected fields present
        assert set(data.keys()) == EXPECTED_RESPONSE_FIELDS

    def test_create_source_with_all_fields(self, client):
        payload = _valid_create_payload(
            port=2121,
            domain="WORKGROUP",
            encoding="shift_jis",
            source_type="HT",
            polling_interval_sec=120,
            collection_mode="full_import",
            parser_pattern=r"(?P<severity>\w+)\s+(?P<message>.+)",
            severity_field="severity",
            default_severity="WARNING",
            is_enabled=False,
        )
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["port"] == 2121
        assert data["domain"] == "WORKGROUP"
        assert data["encoding"] == "shift_jis"
        assert data["source_type"] == "HT"
        assert data["polling_interval_sec"] == 120
        assert data["collection_mode"] == "full_import"
        assert data["parser_pattern"] == r"(?P<severity>\w+)\s+(?P<message>.+)"
        assert data["severity_field"] == "severity"
        assert data["default_severity"] == "WARNING"
        assert data["is_enabled"] is False

    def test_create_source_smb(self, client):
        payload = _valid_create_payload(
            access_method="smb",
            host="fileserver.local",
            domain="CORP",
            paths=[{"base_path": "share/logs", "file_pattern": "*.log"}],
        )
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["access_method"] == "smb"
        assert res.json()["domain"] == "CORP"
        assert res.json()["paths"][0]["base_path"] == "share/logs"

    def test_create_source_multiple_paths(self, client):
        """Create a source with multiple monitoring paths."""
        payload = _valid_create_payload(
            paths=[
                {"base_path": "/var/log/app", "file_pattern": "*.log"},
                {"base_path": "/var/log/web", "file_pattern": "access*.log"},
                {"base_path": "/var/log/batch", "file_pattern": "batch_*.log", "is_enabled": False},
            ]
        )
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert len(data["paths"]) == 3
        paths = sorted(data["paths"], key=lambda p: p["base_path"])
        assert paths[0]["base_path"] == "/var/log/app"
        assert paths[1]["base_path"] == "/var/log/batch"
        assert paths[1]["is_enabled"] is False
        assert paths[2]["base_path"] == "/var/log/web"

    def test_create_source_empty_paths_rejected(self, client):
        """Creating with empty paths list should be rejected."""
        payload = _valid_create_payload(paths=[])
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_list_sources(self, client):
        client.post("/api/log-sources/", json=_valid_create_payload(name="Source 1"))
        client.post("/api/log-sources/", json=_valid_create_payload(name="Source 2"))
        res = client.get("/api/log-sources/")
        assert res.status_code == 200
        data = res.json()
        names = [s["name"] for s in data]
        assert "Source 1" in names
        assert "Source 2" in names

    def test_list_sources_empty(self, client):
        res = client.get("/api/log-sources/")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_source(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload(name="Get Me"))
        source_id = create_res.json()["id"]
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Get Me"
        assert set(res.json().keys()) == EXPECTED_RESPONSE_FIELDS
        # Verify paths included
        assert len(res.json()["paths"]) == 1

    def test_get_source_not_found(self, client):
        res = client.get("/api/log-sources/99999")
        assert res.status_code == 404

    def test_update_source_name(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload(name="Original"))
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"name": "Updated"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_update_source_host_and_port(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(
            f"/api/log-sources/{source_id}",
            json={"host": "10.0.0.99", "port": 2222},
        )
        assert res.status_code == 200
        assert res.json()["host"] == "10.0.0.99"
        assert res.json()["port"] == 2222

    def test_update_source_credentials(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(
            f"/api/log-sources/{source_id}",
            json={"username": "newuser", "password": "newpass"},
        )
        assert res.status_code == 200
        # username_masked should reflect the new username
        assert res.json()["username_masked"] == "n****r"

    def test_update_source_not_found(self, client):
        res = client.put("/api/log-sources/99999", json={"name": "X"})
        assert res.status_code == 404

    def test_update_source_paths_add(self, client):
        """Add a new path to an existing source."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        existing_path = create_res.json()["paths"][0]

        res = client.put(
            f"/api/log-sources/{source_id}",
            json={
                "paths": [
                    {
                        "id": existing_path["id"],
                        "base_path": existing_path["base_path"],
                        "file_pattern": existing_path["file_pattern"],
                    },
                    {"base_path": "/var/log/new", "file_pattern": "new_*.log"},
                ]
            },
        )
        assert res.status_code == 200
        assert len(res.json()["paths"]) == 2

    def test_update_source_paths_remove(self, client):
        """Remove a path from a multi-path source."""
        payload = _valid_create_payload(
            paths=[
                {"base_path": "/var/log/app", "file_pattern": "*.log"},
                {"base_path": "/var/log/web", "file_pattern": "*.log"},
            ]
        )
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]
        path_to_keep = create_res.json()["paths"][0]

        res = client.put(
            f"/api/log-sources/{source_id}",
            json={
                "paths": [
                    {
                        "id": path_to_keep["id"],
                        "base_path": path_to_keep["base_path"],
                        "file_pattern": path_to_keep["file_pattern"],
                    },
                ]
            },
        )
        assert res.status_code == 200
        assert len(res.json()["paths"]) == 1

    def test_update_source_paths_modify(self, client):
        """Modify an existing path's base_path."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        existing_path = create_res.json()["paths"][0]

        res = client.put(
            f"/api/log-sources/{source_id}",
            json={
                "paths": [
                    {"id": existing_path["id"], "base_path": "/var/log/updated", "file_pattern": "updated_*.log"},
                ]
            },
        )
        assert res.status_code == 200
        assert res.json()["paths"][0]["base_path"] == "/var/log/updated"
        assert res.json()["paths"][0]["file_pattern"] == "updated_*.log"

    def test_update_source_paths_empty_rejected(self, client):
        """Update with empty paths list should be rejected."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"paths": []})
        assert res.status_code == 422

    def test_delete_source(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload(name="Delete Me"))
        source_id = create_res.json()["id"]
        res = client.delete(f"/api/log-sources/{source_id}")
        assert res.status_code == 204
        # Verify deletion
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.status_code == 404

    def test_delete_source_not_found(self, client):
        res = client.delete("/api/log-sources/99999")
        assert res.status_code == 404

    def test_toggle_enable(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json=_valid_create_payload(is_enabled=True),
        )
        source_id = create_res.json()["id"]

        res = client.put(f"/api/log-sources/{source_id}", json={"is_enabled": False})
        assert res.status_code == 200
        assert res.json()["is_enabled"] is False

        res = client.put(f"/api/log-sources/{source_id}", json={"is_enabled": True})
        assert res.status_code == 200
        assert res.json()["is_enabled"] is True

    def test_status_endpoint(self, client):
        client.post("/api/log-sources/", json=_valid_create_payload(name="Status Source"))
        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        entry = data[-1]
        assert "id" in entry
        assert "name" in entry
        assert "department_id" in entry
        assert "department_name" in entry
        assert "source_type" in entry
        assert "collection_mode" in entry
        assert "consecutive_errors" in entry
        assert "file_count" in entry
        assert "new_file_count" in entry
        assert "updated_file_count" in entry
        assert "path_count" in entry
        assert entry["path_count"] >= 1

    def test_status_endpoint_path_count(self, client):
        """Verify path_count reflects the number of paths."""
        payload = _valid_create_payload(
            name="Multi-Path Status",
            paths=[
                {"base_path": "/var/log/a", "file_pattern": "*.log"},
                {"base_path": "/var/log/b", "file_pattern": "*.log"},
                {"base_path": "/var/log/c", "file_pattern": "*.log"},
            ],
        )
        client.post("/api/log-sources/", json=payload)
        res = client.get("/api/log-sources/status")
        data = res.json()
        multi_source = next(s for s in data if s["name"] == "Multi-Path Status")
        assert multi_source["path_count"] == 3


class TestLogSourceCredentialMasking:
    """Verify that credentials are masked in API responses."""

    def test_username_masked_in_create_response(self, client):
        res = client.post(
            "/api/log-sources/",
            json=_valid_create_payload(username="loguser"),
        )
        assert res.status_code == 201
        data = res.json()
        # "loguser" -> "l****r"
        assert data["username_masked"] == "l****r"
        # Raw username/password must NOT appear in response
        assert "username" not in data or data.get("username") is None
        assert "password" not in data

    def test_username_masked_in_get_response(self, client):
        create_res = client.post(
            "/api/log-sources/",
            json=_valid_create_payload(username="administrator"),
        )
        source_id = create_res.json()["id"]
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.status_code == 200
        # "administrator" -> "a****r"
        assert res.json()["username_masked"] == "a****r"

    def test_username_masked_in_list_response(self, client):
        client.post(
            "/api/log-sources/",
            json=_valid_create_payload(username="ftpuser"),
        )
        res = client.get("/api/log-sources/")
        assert res.status_code == 200
        sources = res.json()
        assert len(sources) >= 1
        # Find our source and check masking
        last = sources[-1]
        assert "username_masked" in last
        assert "password" not in last

    def test_short_username_fully_masked(self, client):
        res = client.post(
            "/api/log-sources/",
            json=_valid_create_payload(username="ab"),
        )
        assert res.status_code == 201
        # Usernames with 2 or fewer chars -> "****"
        assert res.json()["username_masked"] == "****"

    def test_single_char_username_fully_masked(self, client):
        res = client.post(
            "/api/log-sources/",
            json=_valid_create_payload(username="x"),
        )
        assert res.status_code == 201
        assert res.json()["username_masked"] == "****"


class TestLogSourceValidation:
    """Schema validation tests for log source create/update."""

    def test_invalid_access_method(self, client):
        payload = _valid_create_payload(access_method="ssh")
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_invalid_collection_mode(self, client):
        payload = _valid_create_payload(collection_mode="stream")
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_invalid_source_type(self, client):
        payload = _valid_create_payload(source_type="INVALID")
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_valid_source_types(self, client):
        """All valid source types should be accepted."""
        for source_type in ("WEB", "HT", "BATCH", "OTHER"):
            res = client.post(
                "/api/log-sources/",
                json=_valid_create_payload(name=f"Type {source_type}", source_type=source_type),
            )
            assert res.status_code == 201, f"source_type={source_type} rejected"
            assert res.json()["source_type"] == source_type

    def test_polling_interval_too_low(self, client):
        payload = _valid_create_payload(polling_interval_sec=10)
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_polling_interval_too_high(self, client):
        payload = _valid_create_payload(polling_interval_sec=7200)
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_polling_interval_min_boundary(self, client):
        payload = _valid_create_payload(polling_interval_sec=60)
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["polling_interval_sec"] == 60

    def test_polling_interval_max_boundary(self, client):
        payload = _valid_create_payload(polling_interval_sec=300)
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["polling_interval_sec"] == 300

    def test_invalid_regex_pattern(self, client):
        payload = _valid_create_payload(parser_pattern="[invalid(regex")
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 422

    def test_valid_regex_pattern(self, client):
        payload = _valid_create_payload(parser_pattern=r"(?P<level>\w+)\s+(?P<msg>.+)")
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["parser_pattern"] == r"(?P<level>\w+)\s+(?P<msg>.+)"

    def test_update_invalid_access_method(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"access_method": "sftp"})
        assert res.status_code == 422

    def test_update_invalid_polling_interval(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"polling_interval_sec": 5})
        assert res.status_code == 422

    def test_update_invalid_source_type(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.put(f"/api/log-sources/{source_id}", json={"source_type": "UNKNOWN"})
        assert res.status_code == 422

    def test_missing_required_fields(self, client):
        """Missing required fields should return 422."""
        res = client.post("/api/log-sources/", json={"name": "Incomplete"})
        assert res.status_code == 422


class TestLogSourceRBAC:
    """Authorization tests: admin vs non-admin access control."""

    def test_non_admin_cannot_create_source(self, client_user2):
        res = client_user2.post("/api/log-sources/", json=_valid_create_payload())
        assert res.status_code == 403

    def test_non_admin_cannot_update_source(self, client_user2, db_session):
        source = _create_source_in_db(db_session, name="Admin Source")
        res = client_user2.put(f"/api/log-sources/{source.id}", json={"name": "Hacked"})
        assert res.status_code == 403

    def test_non_admin_cannot_delete_source(self, client_user2, db_session):
        source = _create_source_in_db(db_session, name="Protected")
        res = client_user2.delete(f"/api/log-sources/{source.id}")
        assert res.status_code == 403

    def test_non_admin_can_read_source_list(self, client_user2, db_session):
        _create_source_in_db(db_session, name="Readable")
        res = client_user2.get("/api/log-sources/")
        assert res.status_code == 200
        names = [s["name"] for s in res.json()]
        assert "Readable" in names

    def test_non_admin_can_read_source_detail(self, client_user2, db_session):
        source = _create_source_in_db(db_session, name="Readable Detail")
        res = client_user2.get(f"/api/log-sources/{source.id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Readable Detail"

    def test_non_admin_can_read_source_status(self, client_user2, db_session):
        _create_source_in_db(db_session, name="Status Source")
        res = client_user2.get("/api/log-sources/status")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_non_admin_cannot_test_connection(self, client_user2, db_session):
        source = _create_source_in_db(db_session, name="Test Source")
        res = client_user2.post(f"/api/log-sources/{source.id}/test")
        assert res.status_code == 403

    def test_non_admin_can_list_files(self, client_user2, db_session):
        source = _create_source_in_db(db_session, name="Files Source")
        res = client_user2.get(f"/api/log-sources/{source.id}/files")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestLogSourceConnectionTest:
    """Tests for POST /{id}/test connection test endpoint."""

    def test_connection_test_success(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = [
            MagicMock(name="app.log"),
            MagicMock(name="error.log"),
            MagicMock(name="access.log"),
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["file_count"] == 3
        assert "Connected successfully" in data["message"]
        assert "3 files" in data["message"]
        # Verify path_results
        assert "path_results" in data
        assert len(data["path_results"]) == 1
        assert data["path_results"][0]["status"] == "ok"
        assert data["path_results"][0]["file_count"] == 3

    def test_connection_test_failure(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        with patch(
            "app.services.log_source_service.create_connector",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"
        assert data["file_count"] == 0
        assert "Connection refused" in data["message"]
        assert data["path_results"] == []

    def test_connection_test_timeout(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        with patch(
            "app.services.log_source_service.create_connector",
            side_effect=TimeoutError("Connection timed out"),
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"
        assert data["file_count"] == 0

    def test_connection_test_not_found(self, client):
        res = client.post("/api/log-sources/99999/test")
        assert res.status_code == 404

    def test_connection_test_empty_directory(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = []

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["file_count"] == 0

    def test_connection_test_response_structure(self, client):
        """Verify the response matches ConnectionTestResponse schema."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = []

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "file_count" in data
        assert "message" in data
        assert "path_results" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["file_count"], int)
        assert isinstance(data["message"], str)
        assert isinstance(data["path_results"], list)

    def test_connection_test_multi_path_success(self, client):
        """Test connection with multiple paths - all succeed."""
        payload = _valid_create_payload(
            paths=[
                {"base_path": "/var/log/app", "file_pattern": "*.log"},
                {"base_path": "/var/log/web", "file_pattern": "access*.log"},
            ]
        )
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.side_effect = [
            [MagicMock(name="app.log"), MagicMock(name="error.log")],
            [MagicMock(name="access.log")],
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["file_count"] == 3
        assert len(data["path_results"]) == 2
        assert all(r["status"] == "ok" for r in data["path_results"])

    def test_connection_test_multi_path_partial_failure(self, client):
        """Test connection with multiple paths - one fails."""
        payload = _valid_create_payload(
            paths=[
                {"base_path": "/var/log/app", "file_pattern": "*.log"},
                {"base_path": "/var/log/missing", "file_pattern": "*.log"},
            ]
        )
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.side_effect = [
            [MagicMock(name="app.log")],
            FileNotFoundError("Directory not found"),
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/test")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"
        assert data["file_count"] == 1
        assert len(data["path_results"]) == 2
        assert data["path_results"][0]["status"] == "ok"
        assert data["path_results"][1]["status"] == "error"
        assert "Partial success" in data["message"]


class TestLogSourceFiles:
    """Tests for GET /{id}/files endpoint."""

    def test_list_files_empty(self, client):
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        res = client.get(f"/api/log-sources/{source_id}/files")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_files_not_found(self, client):
        res = client.get("/api/log-sources/99999/files")
        assert res.status_code == 404


class TestLogSourcePathResponseFormat:
    """Tests for path data in responses."""

    def test_path_response_has_all_fields(self, client):
        """Verify path objects in response contain all expected fields."""
        res = client.post("/api/log-sources/", json=_valid_create_payload())
        assert res.status_code == 201
        path = res.json()["paths"][0]
        expected_path_fields = {
            "id",
            "source_id",
            "base_path",
            "file_pattern",
            "is_enabled",
            "created_at",
            "updated_at",
        }
        assert set(path.keys()) == expected_path_fields

    def test_path_default_file_pattern(self, client):
        """Path with default file_pattern should be *.log."""
        payload = _valid_create_payload(paths=[{"base_path": "/var/log/app"}])
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["paths"][0]["file_pattern"] == "*.log"

    def test_path_default_is_enabled(self, client):
        """Path with default is_enabled should be True."""
        payload = _valid_create_payload(paths=[{"base_path": "/var/log/app"}])
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["paths"][0]["is_enabled"] is True

    def test_list_response_includes_paths(self, client):
        """List endpoint should include paths for each source."""
        client.post("/api/log-sources/", json=_valid_create_payload(name="With Paths"))
        res = client.get("/api/log-sources/")
        assert res.status_code == 200
        sources = res.json()
        source = next(s for s in sources if s["name"] == "With Paths")
        assert "paths" in source
        assert len(source["paths"]) >= 1


class TestLogSourceAlertOnChange:
    """Tests for alert_on_change feature."""

    def test_create_source_with_alert_on_change(self, client):
        """Create a source with alert_on_change=True."""
        payload = _valid_create_payload(alert_on_change=True)
        res = client.post("/api/log-sources/", json=payload)
        assert res.status_code == 201
        assert res.json()["alert_on_change"] is True

    def test_create_source_default_alert_off(self, client):
        """Default alert_on_change should be False."""
        res = client.post("/api/log-sources/", json=_valid_create_payload())
        assert res.status_code == 201
        assert res.json()["alert_on_change"] is False

    def test_update_source_alert_on_change(self, client):
        """Update alert_on_change flag."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        res = client.put(f"/api/log-sources/{source_id}", json={"alert_on_change": True})
        assert res.status_code == 200
        assert res.json()["alert_on_change"] is True

        res = client.put(f"/api/log-sources/{source_id}", json={"alert_on_change": False})
        assert res.status_code == 200
        assert res.json()["alert_on_change"] is False

    def test_source_status_has_alert_when_changes(self, client, db_session):
        """Status endpoint should show has_alert=True when alert_on_change + new/updated files."""
        source = _create_source_in_db(db_session, name="Alert Source", alert_on_change=True)
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        # Add a file with "new" status
        log_file = LogFile(
            source_id=source.id,
            path_id=path.id,
            file_name="test.log",
            file_size=100,
            status="new",
        )
        db_session.add(log_file)
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "Alert Source")
        assert found["has_alert"] is True
        assert found["alert_on_change"] is True

    def test_source_status_no_alert_when_disabled(self, client, db_session):
        """has_alert should be False when alert_on_change is False even with new files."""
        source = _create_source_in_db(db_session, name="No Alert Source", alert_on_change=False)
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        log_file = LogFile(
            source_id=source.id,
            path_id=path.id,
            file_name="test.log",
            file_size=100,
            status="new",
        )
        db_session.add(log_file)
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "No Alert Source")
        assert found["has_alert"] is False

    def test_source_status_no_alert_when_no_changes(self, client, db_session):
        """has_alert should be False when no new/updated files."""
        source = _create_source_in_db(db_session, name="Unchanged Source", alert_on_change=True)
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        log_file = LogFile(
            source_id=source.id,
            path_id=path.id,
            file_name="old.log",
            file_size=100,
            status="unchanged",
        )
        db_session.add(log_file)
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "Unchanged Source")
        assert found["has_alert"] is False

    def test_source_status_changed_paths_with_files(self, client, db_session):
        """Status should include changed_paths with file names and folder links when has_alert."""
        source = _create_source_in_db(db_session, name="Changed Paths Source", alert_on_change=True, host="192.168.1.1")
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        # Add new and updated files
        for fname, status in [("new.log", "new"), ("updated.log", "updated"), ("old.log", "unchanged")]:
            db_session.add(
                LogFile(
                    source_id=source.id,
                    path_id=path.id,
                    file_name=fname,
                    file_size=100,
                    status=status,
                )
            )
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "Changed Paths Source")
        assert found["has_alert"] is True
        assert len(found["changed_paths"]) == 1
        cp = found["changed_paths"][0]
        assert cp["path_id"] == path.id
        assert cp["base_path"] == path.base_path
        assert "new.log" in cp["new_files"]
        assert "updated.log" in cp["updated_files"]
        # folder_link should be an FTP link
        assert cp["folder_link"].startswith("ftp://")

    def test_source_status_changed_paths_empty_no_alert(self, client, db_session):
        """changed_paths should be empty when has_alert is False."""
        source = _create_source_in_db(db_session, name="No Change Source", alert_on_change=False)
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        db_session.add(
            LogFile(
                source_id=source.id,
                path_id=path.id,
                file_name="new.log",
                file_size=100,
                status="new",
            )
        )
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "No Change Source")
        assert found["has_alert"] is False
        assert found["changed_paths"] == []

    def test_source_status_smb_folder_link(self, client, db_session):
        """SMB sources should generate file:// folder links."""

        source = _create_source_in_db(
            db_session,
            name="SMB Link Source",
            access_method="smb",
            host="fileserver",
            alert_on_change=True,
            paths=[{"base_path": "share/logs", "file_pattern": "*.log"}],
        )
        path = db_session.query(LogSourcePath).filter_by(source_id=source.id).first()

        db_session.add(
            LogFile(
                source_id=source.id,
                path_id=path.id,
                file_name="err.log",
                file_size=100,
                status="updated",
            )
        )
        db_session.flush()

        res = client.get("/api/log-sources/status")
        assert res.status_code == 200
        found = next(s for s in res.json() if s["name"] == "SMB Link Source")
        assert found["has_alert"] is True
        cp = found["changed_paths"][0]
        assert cp["folder_link"] == "file://///fileserver/share/logs/"


class TestLogSourceScan:
    """Tests for POST /{id}/scan endpoint."""

    def test_scan_source_success(self, client):
        """Scan with mocked connector returns correct counts."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=1024, modified_at=today),
            RemoteFileInfo(name="error.log", size=512, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["file_count"] == 2
        assert data["new_count"] == 2
        assert data["updated_count"] == 0
        assert "Scan completed" in data["message"]

    def test_scan_source_updates_last_checked(self, client):
        """Scan should update last_checked_at."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        # Verify initially null
        assert create_res.json()["last_checked_at"] is None

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = []

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/scan")

        # Verify last_checked_at is updated
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.json()["last_checked_at"] is not None

    def test_scan_source_with_alert(self, client):
        """Scan with alert_on_change=True and changes should create alert."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="new.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["new_count"] == 1
        assert data["alerts_created"] == 1

    def test_scan_source_no_alert_when_flag_off(self, client):
        """Scan with alert_on_change=False should not create alert."""
        payload = _valid_create_payload(alert_on_change=False)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="new.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        assert res.json()["alerts_created"] == 0

    def test_scan_source_today_filter(self, client):
        """Scan passes modified_since=today to list_files for early filtering."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        today_dt = datetime.now(timezone.utc)
        # Connector's list_files with modified_since already filters to today's files
        mock_files = [
            RemoteFileInfo(name="today.log", size=100, modified_at=today_dt),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["file_count"] == 1
        assert data["new_count"] == 1
        # Verify list_files was called with modified_since parameter
        call_kwargs = mock_connector.list_files.call_args
        assert call_kwargs[1].get("modified_since") == datetime.now(timezone.utc).date()

    def test_scan_source_today_filter_uses_utc(self, client):
        """Scan uses UTC date for modified_since, not local date.

        Between 00:00-09:00 JST (= previous day in UTC), the filter date
        should be the UTC date, ensuring consistency with file timestamps
        stored in UTC.
        """
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        # Simulate a fixed UTC time (e.g., 2020-03-10 23:30 UTC = 2020-03-11 08:30 JST)
        fake_utc_now = datetime(2020, 3, 10, 23, 30, 0, tzinfo=timezone.utc)
        expected_date = date(2020, 3, 10)  # UTC date, NOT JST date (2020-03-11)

        mock_files = [
            RemoteFileInfo(name="log.txt", size=50, modified_at=fake_utc_now),
        ]
        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with (
            patch(
                "app.services.log_source_service.create_connector",
                return_value=mock_connector,
            ),
            patch(
                "app.services.log_source_service.datetime",
            ) as mock_dt,
        ):
            mock_dt.now.return_value = fake_utc_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        call_kwargs = mock_connector.list_files.call_args
        assert call_kwargs[1].get("modified_since") == expected_date

    def test_scan_source_not_found(self, client):
        """Scan non-existent source returns 404."""
        res = client.post("/api/log-sources/99999/scan")
        assert res.status_code == 404

    def test_scan_source_non_admin(self, client_user2, db_session):
        """Non-admin cannot scan."""
        source = _create_source_in_db(db_session, name="Scan Source")
        res = client_user2.post(f"/api/log-sources/{source.id}/scan")
        assert res.status_code == 403

    def test_scan_source_connection_error(self, client):
        """Scan with connection error records error and returns message."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        with patch(
            "app.services.log_source_service.create_connector",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["file_count"] == 0
        assert "Scan failed" in data["message"]
        assert data["changed_paths"] == []

        # Verify consecutive_errors incremented
        source_res = client.get(f"/api/log-sources/{source_id}")
        assert source_res.json()["consecutive_errors"] == 1
        assert source_res.json()["last_error"] is not None

    def test_scan_source_changed_paths_in_result(self, client):
        """Scan should return changed_paths with folder links and file names."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=1024, modified_at=today),
            RemoteFileInfo(name="error.log", size=512, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["new_count"] == 2
        assert len(data["changed_paths"]) == 1
        cp = data["changed_paths"][0]
        assert cp["base_path"] == "/var/log/app"
        assert "app.log" in cp["new_files"]
        assert "error.log" in cp["new_files"]
        assert cp["updated_files"] == []
        assert cp["folder_link"].startswith("ftp://")

    def test_scan_source_no_changed_paths_when_no_changes(self, client):
        """Scan with no changes should return empty changed_paths."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = []

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        assert res.json()["changed_paths"] == []


class TestFolderLinkGeneration:
    """Tests for _generate_folder_link helper."""

    def test_ftp_folder_link(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("ftp", "192.168.1.1", None, "/var/log/app")
        assert link == "ftp://192.168.1.1/var/log/app/"

    def test_ftp_folder_link_with_port(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("ftp", "192.168.1.1", 2121, "/var/log/app")
        assert link == "ftp://192.168.1.1:2121/var/log/app/"

    def test_ftp_folder_link_default_port(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("ftp", "192.168.1.1", 21, "/var/log/app")
        assert link == "ftp://192.168.1.1/var/log/app/"

    def test_smb_folder_link(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("smb", "fileserver", None, "share/logs")
        assert link == "file://///fileserver/share/logs/"

    def test_smb_folder_link_backslash_path(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("smb", "fileserver", None, "share\\logs\\subfolder")
        assert link == "file://///fileserver/share/logs/subfolder/"

    def test_folder_link_trailing_slash_normalization(self):
        from app.services.log_source_service import _generate_folder_link

        link = _generate_folder_link("ftp", "host", None, "/logs/app/")
        assert link == "ftp://host/logs/app/"


class TestLogSourceTestConnectionLastChecked:
    """Tests for test_connection updating last_checked_at."""

    def test_test_connection_updates_last_checked(self, client):
        """Successful test_connection should update last_checked_at."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]
        assert create_res.json()["last_checked_at"] is None

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = [MagicMock(name="app.log")]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/test")

        # Verify last_checked_at is now set
        res = client.get(f"/api/log-sources/{source_id}")
        assert res.json()["last_checked_at"] is not None

    def test_test_connection_failure_no_update(self, client):
        """Failed test_connection should NOT update last_checked_at."""
        create_res = client.post("/api/log-sources/", json=_valid_create_payload())
        source_id = create_res.json()["id"]

        with patch(
            "app.services.log_source_service.create_connector",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            client.post(f"/api/log-sources/{source_id}/test")

        res = client.get(f"/api/log-sources/{source_id}")
        assert res.json()["last_checked_at"] is None


class TestScanContentReading:
    """Tests for alert content reading during scan."""

    def test_scan_alert_reads_content(self, client, db_session):
        """alert_on_change=true + changed files → read_lines called, log_entries saved."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="error.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "2026-02-18 ERROR Something went wrong",
            "2026-02-18 INFO Recovery started",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        assert data["content_read_files"] == 1
        # Verify read_lines was called
        mock_connector.read_lines.assert_called_once()
        # Verify log_entries were created (filter by source to avoid pre-existing data)
        entries = (
            db_session.query(LogEntry)
            .join(LogFile, LogEntry.file_id == LogFile.id)
            .filter(LogFile.source_id == source_id)
            .order_by(LogEntry.line_number)
            .all()
        )
        assert len(entries) == 2
        assert entries[0].message == "2026-02-18 ERROR Something went wrong"
        assert entries[1].message == "2026-02-18 INFO Recovery started"

    def test_scan_no_alert_skips_content(self, client):
        """alert_on_change=false → read_lines not called."""
        payload = _valid_create_payload(alert_on_change=False)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        assert res.json()["content_read_files"] == 0
        mock_connector.read_lines.assert_not_called()

    def test_scan_content_incremental_read(self, client, db_session):
        """last_read_line=10 → read_lines called with offset=10."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]
        path_id = create_res.json()["paths"][0]["id"]

        # Pre-create a file with last_read_line=10
        log_file = LogFile(
            source_id=source_id,
            path_id=path_id,
            file_name="error.log",
            file_size=100,
            status="new",
            last_read_line=10,
        )
        db_session.add(log_file)
        db_session.flush()

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="error.log", size=200, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "Line 11 content",
            "Line 12 content",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        assert res.json()["content_read_files"] == 1
        # Verify offset was passed correctly
        call_kwargs = mock_connector.read_lines.call_args
        assert call_kwargs[1].get("offset") == 10 or call_kwargs[0][2] == 10

    def test_scan_content_updates_last_read_line(self, client, db_session):
        """After reading, last_read_line should be updated."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "Line 1",
            "Line 2",
            "Line 3",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/scan")

        # Verify last_read_line was updated
        log_file = db_session.query(LogFile).filter_by(source_id=source_id, file_name="app.log").first()
        assert log_file is not None
        assert log_file.last_read_line == 3

    def test_scan_content_parser_pattern(self, client, db_session):
        """parser_pattern extracts severity correctly."""
        payload = _valid_create_payload(
            alert_on_change=True,
            parser_pattern=r"(?P<severity>\w+)\s+(?P<msg>.+)",
            severity_field="severity",
            default_severity="INFO",
        )
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="parsed.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "ERROR Database connection failed",
            "WARNING High memory usage",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/scan")

        entries = (
            db_session.query(LogEntry)
            .join(LogFile, LogEntry.file_id == LogFile.id)
            .filter(LogFile.source_id == source_id)
            .order_by(LogEntry.line_number)
            .all()
        )
        assert len(entries) == 2
        assert entries[0].severity == "ERROR"
        assert entries[1].severity == "WARNING"

    def test_scan_alert_message_includes_content(self, client, db_session):
        """Alert message should contain log content."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="error.log", size=100, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "CRITICAL System failure detected",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        assert res.json()["alerts_created"] == 1

        # Check alert message in DB
        from app.models.alert import Alert

        alert = db_session.query(Alert).order_by(Alert.id.desc()).first()
        assert alert is not None
        assert "--- Log Content ---" in alert.message
        assert "CRITICAL System failure detected" in alert.message

    def test_scan_content_read_error_isolated(self, client, db_session):
        """One file read error should not affect other files."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="good.log", size=100, modified_at=today),
            RemoteFileInfo(name="bad.log", size=200, modified_at=today),
        ]

        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files

        # read_lines: first file succeeds, second raises error
        mock_connector.read_lines.side_effect = [
            ["Good log line 1", "Good log line 2"],
            IOError("Permission denied"),
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            res = client.post(f"/api/log-sources/{source_id}/scan")

        assert res.status_code == 200
        data = res.json()
        # Only one file was successfully read
        assert data["content_read_files"] == 1
        # Entries from the good file should be saved
        entries = (
            db_session.query(LogEntry)
            .join(LogFile, LogEntry.file_id == LogFile.id)
            .filter(LogFile.source_id == source_id)
            .order_by(LogEntry.line_number)
            .all()
        )
        assert len(entries) == 2
        assert entries[0].message == "Good log line 1"


class TestLogSourceReRead:
    """Tests for re-read (clear entries + reset + re-scan) endpoint."""

    def _get_entries_for_source(self, db_session, source_id):
        """Get log entries belonging to a specific source (via log_files)."""
        return (
            db_session.query(LogEntry)
            .join(LogFile, LogEntry.file_id == LogFile.id)
            .filter(LogFile.source_id == source_id)
            .order_by(LogEntry.line_number)
            .all()
        )

    def test_re_read_clears_entries_and_rescans(self, client, db_session):
        """Re-read should delete old entries and create new ones from re-scan."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        # --- First scan: populate entries ---
        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=100, modified_at=today),
        ]
        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = [
            "Old line 1",
            "Old line 2",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/scan")

        old_entries = self._get_entries_for_source(db_session, source_id)
        assert len(old_entries) == 2
        assert old_entries[0].message == "Old line 1"

        # --- Re-read: should clear old entries and create new ones ---
        mock_connector2 = MagicMock()
        mock_connector2.__enter__ = MagicMock(return_value=mock_connector2)
        mock_connector2.__exit__ = MagicMock(return_value=False)
        mock_connector2.list_files.return_value = mock_files
        mock_connector2.read_lines.return_value = [
            "New line 1",
            "New line 2",
            "New line 3",
        ]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector2,
        ):
            res = client.post(f"/api/log-sources/{source_id}/re-read")

        assert res.status_code == 200
        data = res.json()
        assert data["content_read_files"] == 1

        # Old entries should be gone, new entries should be present
        new_entries = self._get_entries_for_source(db_session, source_id)
        assert len(new_entries) == 3
        assert new_entries[0].message == "New line 1"
        assert new_entries[2].message == "New line 3"

    def test_re_read_resets_last_read_line(self, client, db_session):
        """Re-read should reset last_read_line to 0 before re-scanning."""
        payload = _valid_create_payload(alert_on_change=True)
        create_res = client.post("/api/log-sources/", json=payload)
        source_id = create_res.json()["id"]

        # --- First scan ---
        today = datetime.now(timezone.utc)
        mock_files = [
            RemoteFileInfo(name="app.log", size=100, modified_at=today),
        ]
        mock_connector = MagicMock()
        mock_connector.__enter__ = MagicMock(return_value=mock_connector)
        mock_connector.__exit__ = MagicMock(return_value=False)
        mock_connector.list_files.return_value = mock_files
        mock_connector.read_lines.return_value = ["Line 1", "Line 2"]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector,
        ):
            client.post(f"/api/log-sources/{source_id}/scan")

        # Verify last_read_line was set to 2
        log_file = db_session.query(LogFile).filter(LogFile.source_id == source_id).first()
        assert log_file.last_read_line == 2

        # --- Re-read ---
        mock_connector2 = MagicMock()
        mock_connector2.__enter__ = MagicMock(return_value=mock_connector2)
        mock_connector2.__exit__ = MagicMock(return_value=False)
        mock_connector2.list_files.return_value = mock_files
        mock_connector2.read_lines.return_value = ["Re-read line 1", "Re-read line 2", "Re-read line 3"]

        with patch(
            "app.services.log_source_service.create_connector",
            return_value=mock_connector2,
        ):
            res = client.post(f"/api/log-sources/{source_id}/re-read")

        assert res.status_code == 200

        # last_read_line should now reflect the re-read (3 lines)
        db_session.expire_all()
        log_file = db_session.query(LogFile).filter(LogFile.source_id == source_id).first()
        assert log_file.last_read_line == 3

        # read_lines should have been called with offset=0 (not 2)
        mock_connector2.read_lines.assert_called_once()
        call_kwargs = mock_connector2.read_lines.call_args
        assert call_kwargs[1]["offset"] == 0

    def test_re_read_requires_admin(self, client_user2, db_session):
        """Non-admin users should get 403 on re-read."""
        source = _create_source_in_db(db_session)
        db_session.commit()

        res = client_user2.post(f"/api/log-sources/{source.id}/re-read")
        assert res.status_code == 403


def test_circuit_breaker_config_exists():
    """LOG_SOURCE_MAX_CONSECUTIVE_FAILURES must be defined in config."""
    from app import config

    assert hasattr(config, "LOG_SOURCE_MAX_CONSECUTIVE_FAILURES")
    assert isinstance(config.LOG_SOURCE_MAX_CONSECUTIVE_FAILURES, int)
    assert config.LOG_SOURCE_MAX_CONSECUTIVE_FAILURES > 0


def test_circuit_breaker_auto_disables_after_max_failures(client, db_session):
    """Source must be auto-disabled after LOG_SOURCE_MAX_CONSECUTIVE_FAILURES errors."""
    from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
    from app.crud import log_source as crud_ls

    resp = client.post(
        "/api/log-sources/",
        json={
            "name": "Circuit Breaker Test",
            "department_id": _test_dept_id,
            "access_method": "ftp",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "paths": [{"base_path": "/logs"}],
        },
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]
    source = crud_ls.get_log_source(db_session, source_id)
    assert source.is_enabled is True

    # Simulate consecutive failures up to threshold - 1 (still enabled)
    for i in range(LOG_SOURCE_MAX_CONSECUTIVE_FAILURES - 1):
        crud_ls.update_scan_state(db_session, source, error="connection refused")
        db_session.refresh(source)
        assert source.is_enabled is True, f"Should still be enabled after {i + 1} failures"

    # Final failure — triggers auto-disable
    crud_ls.update_scan_state(db_session, source, error="connection refused")
    db_session.refresh(source)
    assert source.is_enabled is False


def test_circuit_breaker_does_not_disable_on_success(client, db_session):
    """Source must NOT be auto-disabled if errors are intermittent (reset on success)."""
    from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
    from app.crud import log_source as crud_ls

    resp = client.post(
        "/api/log-sources/",
        json={
            "name": "CB Success Reset Test",
            "department_id": _test_dept_id,
            "access_method": "ftp",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "paths": [{"base_path": "/logs"}],
        },
    )
    source_id = resp.json()["id"]
    source = crud_ls.get_log_source(db_session, source_id)

    # Some failures
    for _ in range(LOG_SOURCE_MAX_CONSECUTIVE_FAILURES - 1):
        crud_ls.update_scan_state(db_session, source, error="timeout")
        db_session.refresh(source)

    # Success resets counter
    crud_ls.update_scan_state(db_session, source)
    db_session.refresh(source)
    assert source.consecutive_errors == 0
    assert source.is_enabled is True


def test_circuit_breaker_via_scan_endpoint_disables_source(client):
    """Service layer: POST /api/log-sources/{id}/scan auto-disables source after N consecutive failures."""
    from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES

    resp = client.post(
        "/api/log-sources/",
        json={
            "name": "CB Service Integration Test",
            "department_id": _test_dept_id,
            "access_method": "ftp",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "paths": [{"base_path": "/logs"}],
        },
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    # Call the scan endpoint N times, each raising a connector exception
    for i in range(LOG_SOURCE_MAX_CONSECUTIVE_FAILURES):
        with patch(
            "app.services.log_source_service.create_connector",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            scan_res = client.post(f"/api/log-sources/{source_id}/scan")
        assert scan_res.status_code == 200
        assert "Scan failed" in scan_res.json()["message"]

    # After N failures the source must be auto-disabled
    source_res = client.get(f"/api/log-sources/{source_id}")
    assert source_res.status_code == 200
    data = source_res.json()
    assert data["is_enabled"] is False
    assert data["consecutive_errors"] == LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
