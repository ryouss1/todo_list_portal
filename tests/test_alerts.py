"""Tests for alerts API."""


class TestAlertAPI:
    def test_create_alert(self, client):
        res = client.post(
            "/api/alerts/",
            json={"title": "Test Alert", "message": "Something happened", "severity": "warning"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Test Alert"
        assert data["severity"] == "warning"
        assert data["is_active"] is True
        assert data["acknowledged"] is False

    def test_default_severity(self, client):
        res = client.post(
            "/api/alerts/",
            json={"title": "Info Alert", "message": "Just info"},
        )
        assert res.status_code == 201
        assert res.json()["severity"] == "info"

    def test_list_alerts(self, client):
        client.post("/api/alerts/", json={"title": "A1", "message": "m1"})
        client.post("/api/alerts/", json={"title": "A2", "message": "m2"})
        res = client.get("/api/alerts/")
        assert res.status_code == 200
        assert len(res.json()) >= 2

    def test_list_active_only(self, client):
        client.post("/api/alerts/", json={"title": "Active", "message": "m"})
        r2 = client.post("/api/alerts/", json={"title": "Inactive", "message": "m"})
        client.patch(f"/api/alerts/{r2.json()['id']}/deactivate")
        res = client.get("/api/alerts/?active_only=true")
        assert res.status_code == 200
        titles = [a["title"] for a in res.json()]
        assert "Active" in titles
        assert "Inactive" not in titles

    def test_get_alert(self, client):
        create_res = client.post("/api/alerts/", json={"title": "Get Me", "message": "m"})
        alert_id = create_res.json()["id"]
        res = client.get(f"/api/alerts/{alert_id}")
        assert res.status_code == 200
        assert res.json()["title"] == "Get Me"

    def test_get_alert_not_found(self, client):
        res = client.get("/api/alerts/99999")
        assert res.status_code == 404

    def test_acknowledge_alert(self, client):
        create_res = client.post("/api/alerts/", json={"title": "Ack Me", "message": "m"})
        alert_id = create_res.json()["id"]
        res = client.patch(f"/api/alerts/{alert_id}/acknowledge")
        assert res.status_code == 200
        data = res.json()
        assert data["acknowledged"] is True
        assert data["acknowledged_by"] == 1
        assert data["acknowledged_at"] is not None

    def test_deactivate_alert(self, client):
        create_res = client.post("/api/alerts/", json={"title": "Deact", "message": "m"})
        alert_id = create_res.json()["id"]
        res = client.patch(f"/api/alerts/{alert_id}/deactivate")
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_unacknowledged_count(self, client):
        client.post("/api/alerts/", json={"title": "A1", "message": "m"})
        client.post("/api/alerts/", json={"title": "A2", "message": "m"})
        r3 = client.post("/api/alerts/", json={"title": "A3", "message": "m"})
        client.patch(f"/api/alerts/{r3.json()['id']}/acknowledge")
        res = client.get("/api/alerts/count")
        assert res.status_code == 200
        assert res.json()["count"] >= 2

    def test_delete_alert(self, client):
        """ISSUE-042: Admin can delete alerts."""
        create_res = client.post("/api/alerts/", json={"title": "Delete Me", "message": "m"})
        alert_id = create_res.json()["id"]
        res = client.delete(f"/api/alerts/{alert_id}")
        assert res.status_code == 204
        res = client.get(f"/api/alerts/{alert_id}")
        assert res.status_code == 404

    def test_delete_alert_not_found(self, client):
        res = client.delete("/api/alerts/99999")
        assert res.status_code == 404


class TestAlertSeverityValidation:
    """ISSUE-026+035: Severity Literal validation tests."""

    def test_invalid_severity_rejected(self, client):
        res = client.post(
            "/api/alerts/",
            json={"title": "Bad", "message": "m", "severity": "INVALID"},
        )
        assert res.status_code == 422

    def test_empty_severity_rejected(self, client):
        res = client.post(
            "/api/alerts/",
            json={"title": "Bad", "message": "m", "severity": ""},
        )
        assert res.status_code == 422

    def test_mixed_case_severity_rejected(self, client):
        """Only lowercase values are valid for alert severity."""
        res = client.post(
            "/api/alerts/",
            json={"title": "Bad", "message": "m", "severity": "Warning"},
        )
        assert res.status_code == 422

    def test_valid_severities(self, client):
        for sev in ("info", "warning", "critical"):
            res = client.post(
                "/api/alerts/",
                json={"title": f"Sev {sev}", "message": "m", "severity": sev},
            )
            assert res.status_code == 201, f"Severity '{sev}' should be valid"


class TestAlertFilterPage:
    """Test alerts page has filter bar elements."""

    def test_alerts_page_has_filter_bar(self, client):
        res = client.get("/alerts")
        assert res.status_code == 200
        html = res.text
        assert 'id="alert-filter-bar"' in html
        assert 'id="alert-source-filter"' in html
        assert 'id="alert-keyword-filter"' in html
        assert 'data-severity="all"' in html
        assert 'data-severity="info"' in html
        assert 'data-severity="warning"' in html
        assert 'data-severity="critical"' in html


class TestAlertRBAC:
    """ISSUE-033: Non-admin users cannot delete alerts."""

    def test_non_admin_cannot_delete_alert(self, client_user2, db_session):
        from app.models.alert import Alert

        alert = Alert(title="Protected", message="m", severity="info")
        db_session.add(alert)
        db_session.flush()
        res = client_user2.delete(f"/api/alerts/{alert.id}")
        assert res.status_code == 403
