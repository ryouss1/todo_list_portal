from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.alert import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate
from app.services import alert_service as svc

router = APIRouter(prefix="/api/alert-rules", tags=["alert-rules"])


@router.get("/", response_model=List[AlertRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_rules(db)


@router.post("/", response_model=AlertRuleResponse, status_code=201)
def create_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.create_rule(db, data)


@router.get("/{rule_id}", response_model=AlertRuleResponse)
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_rule(db, rule_id)


@router.put("/{rule_id}", response_model=AlertRuleResponse)
def update_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.update_rule(db, rule_id, data)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_rule(db, rule_id)
