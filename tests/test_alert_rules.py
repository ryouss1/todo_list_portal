"""Tests for alert rules API and rule evaluation engine."""

from app.services.alert_service import _matches_condition


class TestAlertRuleCRUD:
    def test_create_rule(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Error Rule",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "{severity} in {system_name}",
                "severity": "critical",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Error Rule"
        assert data["condition"] == {"severity": "ERROR"}
        assert data["is_enabled"] is True

    def test_list_rules(self, client):
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Rule 1",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Rule 2",
                "condition": {"severity": "WARNING"},
                "alert_title_template": "Warning",
            },
        )
        res = client.get("/api/alert-rules/")
        assert res.status_code == 200
        assert len(res.json()) >= 2

    def test_get_rule(self, client):
        create_res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Get Me",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        rule_id = create_res.json()["id"]
        res = client.get(f"/api/alert-rules/{rule_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Get Me"

    def test_get_rule_not_found(self, client):
        res = client.get("/api/alert-rules/99999")
        assert res.status_code == 404

    def test_update_rule(self, client):
        create_res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Original",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        rule_id = create_res.json()["id"]
        res = client.put(f"/api/alert-rules/{rule_id}", json={"name": "Updated"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_delete_rule(self, client):
        create_res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Delete Me",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        rule_id = create_res.json()["id"]
        res = client.delete(f"/api/alert-rules/{rule_id}")
        assert res.status_code == 204
        res = client.get(f"/api/alert-rules/{rule_id}")
        assert res.status_code == 404

    def test_toggle_rule(self, client):
        create_res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Toggle",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        rule_id = create_res.json()["id"]
        res = client.put(f"/api/alert-rules/{rule_id}", json={"is_enabled": False})
        assert res.status_code == 200
        assert res.json()["is_enabled"] is False


class TestAlertRuleSeverityValidation:
    """ISSUE-026+035: Severity Literal validation tests for alert rules."""

    def test_invalid_rule_severity_rejected(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Bad",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
                "severity": "INVALID",
            },
        )
        assert res.status_code == 422

    def test_empty_rule_severity_rejected(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Bad",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
                "severity": "",
            },
        )
        assert res.status_code == 422


class TestAlertRuleConditionValidation:
    """ISSUE-039: Condition schema validation tests."""

    def test_empty_condition_rejected(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Empty Cond",
                "condition": {},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 422

    def test_unknown_operator_rejected(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Unknown Op",
                "condition": {"severity": {"$unknown": "value"}},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 422

    def test_list_value_rejected(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "List Value",
                "condition": {"severity": [1, 2, 3]},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 422

    def test_valid_in_operator_accepted(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "In Op",
                "condition": {"severity": {"$in": ["ERROR", "CRITICAL"]}},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 201

    def test_valid_contains_operator_accepted(self, client):
        res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Contains Op",
                "condition": {"message": {"$contains": "database"}},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 201


class TestAlertRuleRBAC:
    """ISSUE-033: Authorization tests for alert rule management."""

    def test_non_admin_cannot_create_rule(self, client_user2):
        res = client_user2.post(
            "/api/alert-rules/",
            json={
                "name": "Unauthorized",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
            },
        )
        assert res.status_code == 403

    def test_non_admin_cannot_update_rule(self, client_user2, db_session):
        from app.models.alert import AlertRule

        rule = AlertRule(
            name="Admin Rule",
            condition={"severity": "ERROR"},
            alert_title_template="Error",
        )
        db_session.add(rule)
        db_session.flush()
        res = client_user2.put(f"/api/alert-rules/{rule.id}", json={"name": "Hacked"})
        assert res.status_code == 403

    def test_non_admin_cannot_delete_rule(self, client_user2, db_session):
        from app.models.alert import AlertRule

        rule = AlertRule(
            name="Protected",
            condition={"severity": "ERROR"},
            alert_title_template="Error",
        )
        db_session.add(rule)
        db_session.flush()
        res = client_user2.delete(f"/api/alert-rules/{rule.id}")
        assert res.status_code == 403

    def test_non_admin_can_read_rules(self, client_user2, db_session):
        """Non-admin users can read alert rule list."""
        from app.models.alert import AlertRule

        rule = AlertRule(
            name="Readable",
            condition={"severity": "ERROR"},
            alert_title_template="Error",
        )
        db_session.add(rule)
        db_session.flush()
        res = client_user2.get("/api/alert-rules/")
        assert res.status_code == 200


class TestRuleEvaluation:
    def test_exact_match(self):
        assert _matches_condition({"severity": "ERROR"}, {"severity": "ERROR", "message": "test"})

    def test_no_match(self):
        assert not _matches_condition({"severity": "ERROR"}, {"severity": "INFO", "message": "test"})

    def test_in_operator(self):
        condition = {"severity": {"$in": ["ERROR", "CRITICAL"]}}
        assert _matches_condition(condition, {"severity": "ERROR"})
        assert _matches_condition(condition, {"severity": "CRITICAL"})
        assert not _matches_condition(condition, {"severity": "INFO"})

    def test_contains_operator(self):
        condition = {"message": {"$contains": "database"}}
        assert _matches_condition(condition, {"message": "database connection failed"})
        assert not _matches_condition(condition, {"message": "server started"})

    def test_multiple_conditions_and(self):
        condition = {"severity": "ERROR", "system_name": "app-server"}
        assert _matches_condition(condition, {"severity": "ERROR", "system_name": "app-server"})
        assert not _matches_condition(condition, {"severity": "ERROR", "system_name": "other"})
        assert not _matches_condition(condition, {"severity": "INFO", "system_name": "app-server"})

    def test_missing_field_no_match(self):
        assert not _matches_condition({"severity": "ERROR"}, {"message": "test"})

    def test_unknown_operator_no_match(self):
        """Unknown operators should return False (no match)."""
        assert not _matches_condition({"severity": {"$unknown": "val"}}, {"severity": "ERROR"})


class TestRuleEvaluationIntegration:
    def test_log_triggers_alert(self, client):
        # Create an alert rule
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Error Alert",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "{severity} in {system_name}",
                "alert_message_template": "{message}",
                "severity": "critical",
            },
        )
        # Create a log that matches the rule
        client.post(
            "/api/logs/",
            json={
                "system_name": "test-app",
                "log_type": "application",
                "severity": "ERROR",
                "message": "Database connection failed",
            },
        )
        # Check that an alert was generated
        res = client.get("/api/alerts/")
        alerts = res.json()
        auto_alerts = [a for a in alerts if a["rule_id"] is not None]
        assert len(auto_alerts) >= 1
        assert "ERROR in test-app" in auto_alerts[0]["title"]
        assert auto_alerts[0]["severity"] == "critical"

    def test_disabled_rule_no_alert(self, client):
        # Create a disabled rule
        rule_res = client.post(
            "/api/alert-rules/",
            json={
                "name": "Disabled Rule",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Error",
                "is_enabled": False,
            },
        )
        # Create a matching log
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "severity": "ERROR",
                "message": "test",
            },
        )
        # No auto-alerts should be generated from this rule
        res = client.get("/api/alerts/")
        auto_alerts = [a for a in res.json() if a["rule_id"] == rule_res.json()["id"]]
        assert len(auto_alerts) == 0

    def test_template_variables(self, client):
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Template Test",
                "condition": {"severity": "CRITICAL"},
                "alert_title_template": "{severity} alert from {system_name}",
                "alert_message_template": "Log: {message}",
                "severity": "critical",
            },
        )
        client.post(
            "/api/logs/",
            json={
                "system_name": "prod-server",
                "log_type": "system",
                "severity": "CRITICAL",
                "message": "Disk full",
            },
        )
        res = client.get("/api/alerts/")
        auto_alerts = [a for a in res.json() if a["rule_id"] is not None]
        assert len(auto_alerts) >= 1
        alert = auto_alerts[0]
        assert alert["title"] == "CRITICAL alert from prod-server"
        assert alert["message"] == "Log: Disk full"

    def test_multiple_rules_match_same_log(self, client):
        """ISSUE-036: Multiple rules can match the same log entry."""
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Rule A",
                "condition": {"severity": "ERROR"},
                "alert_title_template": "Rule A: {message}",
                "severity": "warning",
            },
        )
        client.post(
            "/api/alert-rules/",
            json={
                "name": "Rule B",
                "condition": {"severity": {"$in": ["ERROR", "CRITICAL"]}},
                "alert_title_template": "Rule B: {message}",
                "severity": "critical",
            },
        )
        client.post(
            "/api/logs/",
            json={
                "system_name": "test",
                "log_type": "app",
                "severity": "ERROR",
                "message": "Multi-match test",
            },
        )
        res = client.get("/api/alerts/")
        auto_alerts = [a for a in res.json() if a["rule_id"] is not None]
        assert len(auto_alerts) >= 2


class TestPagination:
    def test_list_rules_limit(self, client, db_session):
        """GET /api/alert-rules/ should support limit parameter."""
        from app.models.alert import AlertRule

        for i in range(3):
            db_session.add(
                AlertRule(
                    name=f"Rule {i}",
                    condition={"severity": "ERROR"},
                    alert_title_template="Test",
                )
            )
        db_session.flush()

        resp = client.get("/api/alert-rules/?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1
