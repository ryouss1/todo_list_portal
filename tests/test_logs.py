class TestLogAPI:
    def test_create_log(self, client):
        resp = client.post(
            "/api/logs/",
            json={
                "system_name": "test-system",
                "log_type": "app",
                "severity": "ERROR",
                "message": "Test error message",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["system_name"] == "test-system"
        assert data["log_type"] == "app"
        assert data["severity"] == "ERROR"
        assert data["message"] == "Test error message"
        assert data["received_at"] is not None

    def test_create_log_with_extra_data(self, client):
        resp = client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "message": "With extra",
                "extra_data": {"key": "value", "count": 42},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["extra_data"]["key"] == "value"
        assert data["extra_data"]["count"] == 42

    def test_create_log_default_severity(self, client):
        resp = client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "message": "Default severity",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "INFO"

    def test_list_logs(self, client):
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "message": "Log 1",
            },
        )
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "message": "Log 2",
            },
        )

        resp = client.get("/api/logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_list_logs_with_limit(self, client):
        for i in range(5):
            client.post(
                "/api/logs/",
                json={
                    "system_name": "test",
                    "log_type": "app",
                    "message": f"Log {i}",
                },
            )

        resp = client.get("/api/logs/?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) <= 3

    def test_list_important_logs(self, client):
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "severity": "INFO",
                "message": "Not important",
            },
        )
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "severity": "ERROR",
                "message": "Important error",
            },
        )
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "severity": "WARNING",
                "message": "Important warning",
            },
        )

        resp = client.get("/api/logs/important")
        assert resp.status_code == 200
        data = resp.json()
        for log in data:
            assert log["severity"] in ["WARNING", "ERROR", "CRITICAL"]

    def test_create_log_missing_fields(self, client):
        resp = client.post("/api/logs/", json={"system_name": "test"})
        assert resp.status_code == 422
