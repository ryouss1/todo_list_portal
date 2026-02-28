"""Tests for GET /api/jobs/status endpoint."""


class TestJobsStatusEndpoint:
    def test_get_jobs_status_admin(self, client):
        """Admin can GET /api/jobs/status and receive job list."""
        resp = client.get("/api/jobs/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        assert len(data["jobs"]) == 3

        names = {j["name"] for j in data["jobs"]}
        assert names == {"log_scanner", "site_checker", "reminder_checker"}

        for job in data["jobs"]:
            assert "enabled" in job
            assert "running" in job
            assert "last_run_at" in job

    def test_jobs_status_returns_correct_structure(self, client):
        """Each job entry has exactly the expected fields."""
        resp = client.get("/api/jobs/status")
        assert resp.status_code == 200
        for job in resp.json()["jobs"]:
            assert set(job.keys()) == {"name", "enabled", "running", "last_run_at"}
