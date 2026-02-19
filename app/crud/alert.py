from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.alert import Alert, AlertRule
from app.schemas.alert import AlertCreate, AlertRuleCreate, AlertRuleUpdate

_crud_rule = CRUDBase(AlertRule)
_crud_alert = CRUDBase(Alert)

# --- Alert Rules ---


def create_alert_rule(db: Session, data: AlertRuleCreate) -> AlertRule:
    return _crud_rule.create(db, data)


def get_alert_rules(db: Session) -> List[AlertRule]:
    return db.query(AlertRule).order_by(AlertRule.id).all()


def get_enabled_alert_rules(db: Session) -> List[AlertRule]:
    return db.query(AlertRule).filter(AlertRule.is_enabled.is_(True)).order_by(AlertRule.id).all()


get_alert_rule = _crud_rule.get


def update_alert_rule(db: Session, rule: AlertRule, data: AlertRuleUpdate) -> AlertRule:
    return _crud_rule.update(db, rule, data)


delete_alert_rule = _crud_rule.delete


# --- Alerts ---


def create_alert(db: Session, data: AlertCreate, rule_id: Optional[int] = None) -> Alert:
    return _crud_alert.create(db, data, rule_id=rule_id)


def get_alerts(db: Session, active_only: bool = False, limit: int = 100) -> List[Alert]:
    query = db.query(Alert)
    if active_only:
        query = query.filter(Alert.is_active.is_(True))
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


get_alert = _crud_alert.get


def acknowledge_alert(db: Session, alert: Alert, user_id: int) -> Alert:
    alert.acknowledged = True
    alert.acknowledged_by = user_id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def deactivate_alert(db: Session, alert: Alert) -> Alert:
    alert.is_active = False
    db.commit()
    db.refresh(alert)
    return alert


delete_alert = _crud_alert.delete


def count_unacknowledged_alerts(db: Session) -> int:
    return db.query(Alert).filter(Alert.acknowledged.is_(False), Alert.is_active.is_(True)).count()
