from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from app.core.constants import AlertSeverityType

ALERT_SEVERITIES = ("info", "warning", "critical")
AlertSeverity = AlertSeverityType

# --- Alert Rules ---


VALID_CONDITION_OPERATORS = {"$in", "$contains"}


def _validate_condition(v: dict) -> dict:
    """Validate alert rule condition: must be non-empty, values must be valid."""
    if not v:
        raise ValueError("condition must not be empty")
    for field, expected in v.items():
        if not isinstance(field, str):
            raise ValueError("condition keys must be strings")
        if isinstance(expected, dict):
            unknown = set(expected.keys()) - VALID_CONDITION_OPERATORS
            if unknown:
                raise ValueError(f"Unknown operator(s) in condition: {', '.join(unknown)}")
            if not expected:
                raise ValueError(f"condition['{field}'] operator dict must not be empty")
        elif isinstance(expected, (list, tuple)):
            raise ValueError(f"condition['{field}'] value must be a string or operator dict, not a list")
    return v


class AlertRuleCreate(BaseModel):
    name: str
    condition: dict
    alert_title_template: str
    alert_message_template: Optional[str] = None
    severity: AlertSeverity = "warning"
    is_enabled: bool = True

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: dict) -> dict:
        return _validate_condition(v)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[dict] = None
    alert_title_template: Optional[str] = None
    alert_message_template: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    is_enabled: Optional[bool] = None

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: Optional[dict]) -> Optional[dict]:
        if v is not None:
            return _validate_condition(v)
        return v


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    condition: Any
    alert_title_template: str
    alert_message_template: Optional[str] = None
    severity: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Alerts ---


class AlertCreate(BaseModel):
    title: str
    message: str
    severity: AlertSeverity = "info"
    source: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    source: Optional[str] = None
    rule_id: Optional[int] = None
    is_active: bool
    acknowledged: bool
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertCountResponse(BaseModel):
    count: int
