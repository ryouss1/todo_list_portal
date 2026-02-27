from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from portal_core.core.auth.audit import log_auth_event
from portal_core.core.deps import require_admin
from portal_core.core.exceptions import AuthenticationError
from portal_core.crud import auth_audit_log as crud_audit
from portal_core.crud import user as crud_user
from portal_core.database import get_db
from portal_core.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    ValidateTokenRequest,
)
from portal_core.services import auth_service, password_reset_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request (supports X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    user = auth_service.authenticate(
        db,
        body.email,
        body.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    # Prevent session fixation: clear old session then atomically set new data
    request.session.clear()
    request.session.update(
        {
            "user_id": user.id,
            "display_name": user.display_name,
            "session_version": user.session_version,
            "locale": user.preferred_locale or "ja",
        }
    )
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        preferred_locale=user.preferred_locale or "ja",
    )


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        log_auth_event(db, "logout", user_id=user_id, ip_address=_get_client_ip(request))
        db.commit()
    request.session.clear()
    return None


@router.get("/me", response_model=LoginResponse)
def me(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise AuthenticationError()
    user = crud_user.get_user(db, user_id)
    if not user:
        request.session.clear()
        raise AuthenticationError()
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        preferred_locale=user.preferred_locale or "ja",
    )


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    event_type: str
    email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    password_reset_service.request_password_reset(db, body.email, ip_address=ip_address, user_agent=user_agent)
    return {"detail": "If an account with that email exists, a reset link has been sent."}


@router.post("/validate-reset-token")
def validate_reset_token(body: ValidateTokenRequest, db: Session = Depends(get_db)):
    valid = password_reset_service.validate_reset_token(db, body.token)
    return {"valid": valid}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    password_reset_service.complete_password_reset(
        db, body.token, body.new_password, ip_address=ip_address, user_agent=user_agent
    )
    return {"detail": "Password has been reset successfully."}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin_id: int = Depends(require_admin),
):
    return crud_audit.get_logs(db, limit=limit, user_id=user_id, event_type=event_type)
