import logging
import string
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.crud import alert as crud_alert
from app.models.alert import Alert, AlertRule
from app.schemas.alert import AlertCreate, AlertRuleCreate, AlertRuleUpdate
from app.services.websocket_manager import alert_ws_manager

logger = logging.getLogger("app.services.alert")


# --- Alert Rules ---


async def create_rule(db: Session, data: AlertRuleCreate) -> AlertRule:
    logger.info("Creating alert rule: name=%s", data.name)
    return crud_alert.create_alert_rule(db, data)


async def list_rules(db: Session) -> List[AlertRule]:
    return crud_alert.get_alert_rules(db)


async def get_rule(db: Session, rule_id: int) -> AlertRule:
    rule = crud_alert.get_alert_rule(db, rule_id)
    if not rule:
        raise NotFoundError("Alert rule not found")
    return rule


async def update_rule(db: Session, rule_id: int, data: AlertRuleUpdate) -> AlertRule:
    rule = await get_rule(db, rule_id)
    logger.info("Updating alert rule: id=%d", rule_id)
    return crud_alert.update_alert_rule(db, rule, data)


async def delete_rule(db: Session, rule_id: int) -> None:
    rule = await get_rule(db, rule_id)
    logger.info("Deleting alert rule: id=%d", rule_id)
    crud_alert.delete_alert_rule(db, rule)


# --- Alerts ---


async def create_alert(db: Session, data: AlertCreate) -> Alert:
    logger.info("Creating manual alert: title=%s", data.title)
    alert = crud_alert.create_alert(db, data)
    await _broadcast_alert(alert)
    return alert


async def list_alerts(db: Session, active_only: bool = False, limit: int = 100) -> List[Alert]:
    return crud_alert.get_alerts(db, active_only=active_only, limit=limit)


async def get_alert(db: Session, alert_id: int) -> Alert:
    alert = crud_alert.get_alert(db, alert_id)
    if not alert:
        raise NotFoundError("Alert not found")
    return alert


async def acknowledge_alert(db: Session, alert_id: int, user_id: int) -> Alert:
    alert = await get_alert(db, alert_id)
    logger.info("Acknowledging alert: id=%d by user=%d", alert_id, user_id)
    return crud_alert.acknowledge_alert(db, alert, user_id)


async def deactivate_alert(db: Session, alert_id: int) -> Alert:
    alert = await get_alert(db, alert_id)
    logger.info("Deactivating alert: id=%d", alert_id)
    return crud_alert.deactivate_alert(db, alert)


async def delete_alert(db: Session, alert_id: int) -> None:
    alert = await get_alert(db, alert_id)
    logger.info("Deleting alert: id=%d", alert_id)
    crud_alert.delete_alert(db, alert)


async def count_unacknowledged(db: Session) -> int:
    return crud_alert.count_unacknowledged_alerts(db)


# --- Rule evaluation ---


def _matches_condition(condition: Dict[str, Any], log_data: Dict[str, Any]) -> bool:
    """Check if log_data matches all conditions (AND logic)."""
    for field, expected in condition.items():
        actual = log_data.get(field)
        if actual is None:
            return False
        if isinstance(expected, dict):
            if "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif "$contains" in expected:
                if expected["$contains"] not in str(actual):
                    return False
            else:
                return False
        else:
            if actual != expected:
                return False
    return True


async def evaluate_rules_for_log(db: Session, log_data: Dict[str, Any]) -> None:
    """Evaluate all enabled alert rules against a log entry."""
    rules = crud_alert.get_enabled_alert_rules(db)
    for rule in rules:
        if _matches_condition(rule.condition, log_data):
            title = _safe_substitute(rule.alert_title_template, log_data)
            message = log_data.get("message", "")
            if rule.alert_message_template:
                message = _safe_substitute(rule.alert_message_template, log_data)

            alert_data = AlertCreate(
                title=title,
                message=message,
                severity=rule.severity,
                source=log_data.get("system_name"),
            )
            alert = crud_alert.create_alert(db, alert_data, rule_id=rule.id)
            logger.info("Alert generated from rule '%s' for log: %s", rule.name, title)
            await _broadcast_alert(alert)


def _safe_substitute(template_str: str, data: Dict[str, Any]) -> str:
    """Safely substitute template variables using string.Template.

    Converts {variable} syntax to ${variable} for safe substitution,
    avoiding format string injection risks from str.format_map.
    """
    import re

    safe_data = {k: str(v) if v is not None else "" for k, v in data.items()}
    converted = re.sub(r"\{(\w+)\}", r"${\1}", template_str)
    try:
        return string.Template(converted).safe_substitute(safe_data)
    except (ValueError, KeyError):
        return template_str


async def _broadcast_alert(alert: Alert) -> None:
    """Broadcast alert via WebSocket."""
    await alert_ws_manager.broadcast(
        {
            "type": "new_alert",
            "alert": {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "source": alert.source,
                "rule_id": alert.rule_id,
                "is_active": alert.is_active,
                "acknowledged": alert.acknowledged,
                "created_at": alert.created_at.isoformat(),
            },
        }
    )
