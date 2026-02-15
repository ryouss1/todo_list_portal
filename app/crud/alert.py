from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertRule
from app.schemas.alert import AlertCreate, AlertRuleCreate, AlertRuleUpdate

# --- Alert Rules ---


def create_alert_rule(db: Session, data: AlertRuleCreate) -> AlertRule:
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_alert_rules(db: Session) -> List[AlertRule]:
    return db.query(AlertRule).order_by(AlertRule.id).all()


def get_enabled_alert_rules(db: Session) -> List[AlertRule]:
    return db.query(AlertRule).filter(AlertRule.is_enabled.is_(True)).order_by(AlertRule.id).all()


def get_alert_rule(db: Session, rule_id: int) -> Optional[AlertRule]:
    return db.query(AlertRule).filter(AlertRule.id == rule_id).first()


def update_alert_rule(db: Session, rule: AlertRule, data: AlertRuleUpdate) -> AlertRule:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_alert_rule(db: Session, rule: AlertRule) -> None:
    db.delete(rule)
    db.commit()


# --- Alerts ---


def create_alert(db: Session, data: AlertCreate, rule_id: Optional[int] = None) -> Alert:
    alert = Alert(
        title=data.title,
        message=data.message,
        severity=data.severity,
        source=data.source,
        rule_id=rule_id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts(db: Session, active_only: bool = False, limit: int = 100) -> List[Alert]:
    query = db.query(Alert)
    if active_only:
        query = query.filter(Alert.is_active.is_(True))
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


def get_alert(db: Session, alert_id: int) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()


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


def delete_alert(db: Session, alert: Alert) -> None:
    db.delete(alert)
    db.commit()


def count_unacknowledged_alerts(db: Session) -> int:
    return db.query(Alert).filter(Alert.acknowledged.is_(False), Alert.is_active.is_(True)).count()
