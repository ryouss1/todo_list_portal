"""Business logic for site groups and site links."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import SITE_CHECK_MAX_REDIRECTS
from app.core.constants import UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.crud import site_link as crud
from app.crud import user as crud_user
from app.models.site_link import SiteGroup, SiteLink
from app.schemas.site_link import (
    SiteCheckResponse,
    SiteGroupCreate,
    SiteGroupResponse,
    SiteGroupUpdate,
    SiteLinkCreate,
    SiteLinkResponse,
    SiteLinkUpdate,
    SiteUrlResponse,
)

logger = logging.getLogger("app.services.site_link")

# HTTP status range considered "up" (2xx and 3xx)
_HTTP_SUCCESS_MIN = 200
_HTTP_SUCCESS_MAX = 399

# Maximum length for error messages stored in last_error
_SITE_ERROR_MAX_LENGTH = 200


# ── helpers ──────────────────────────────────────────────────────────────────


def _to_group_response(group: SiteGroup, db: Session, counts_map: Optional[dict] = None) -> SiteGroupResponse:
    if counts_map is not None:
        link_count = counts_map.get(group.id, 0)
    else:
        link_count = crud.count_links_by_group(db, group.id)
    return SiteGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        icon=group.icon,
        sort_order=group.sort_order,
        link_count=link_count,
    )


def _to_link_response(link: SiteLink) -> SiteLinkResponse:
    response = SiteLinkResponse.model_validate(link)
    response.group_name = link.group.name if link.group else None
    return response


# ── SiteGroup service ─────────────────────────────────────────────────────────


def list_groups(db: Session) -> List[SiteGroupResponse]:
    groups = crud.get_groups(db)
    counts_map = crud.count_links_all_groups(db)
    return [_to_group_response(g, db, counts_map=counts_map) for g in groups]


def get_group(db: Session, group_id: int) -> SiteGroupResponse:
    group = crud.get_group(db, group_id)
    if not group:
        raise NotFoundError("Site group not found")
    return _to_group_response(group, db)


def create_group(db: Session, data: SiteGroupCreate) -> SiteGroupResponse:
    existing = crud.get_group_by_name(db, data.name)
    if existing:
        raise ConflictError("Site group name already exists")
    group = crud.create_group(db, data)
    return _to_group_response(group, db)


def update_group(db: Session, group_id: int, data: SiteGroupUpdate) -> SiteGroupResponse:
    group = crud.get_group(db, group_id)
    if not group:
        raise NotFoundError("Site group not found")
    if data.name is not None and data.name != group.name:
        existing = crud.get_group_by_name(db, data.name)
        if existing:
            raise ConflictError("Site group name already exists")
    group = crud.update_group(db, group, data)
    return _to_group_response(group, db)


def delete_group(db: Session, group_id: int) -> None:
    group = crud.get_group(db, group_id)
    if not group:
        raise NotFoundError("Site group not found")
    crud.delete_group(db, group)


# ── SiteLink service ──────────────────────────────────────────────────────────


def list_links(db: Session) -> List[SiteLinkResponse]:
    links = crud.get_links(db)
    return [_to_link_response(link) for link in links]


def get_link(db: Session, link_id: int) -> SiteLinkResponse:
    link = crud.get_link(db, link_id)
    if not link:
        raise NotFoundError("Site link not found")
    return _to_link_response(link)


def get_link_url(db: Session, link_id: int, user_id: int) -> SiteUrlResponse:
    link = crud.get_link(db, link_id)
    if not link:
        raise NotFoundError("Site link not found")
    _check_owner_or_admin(db, link, user_id)
    return SiteUrlResponse(id=link.id, url=link.url)


def create_link(db: Session, data: SiteLinkCreate, user_id: int) -> SiteLinkResponse:
    if data.group_id is not None:
        if not crud.get_group(db, data.group_id):
            raise NotFoundError("Site group not found")
    link = crud.create_link(db, data, user_id)
    return _to_link_response(link)


def update_link(db: Session, link_id: int, data: SiteLinkUpdate, user_id: int) -> SiteLinkResponse:
    link = crud.get_link(db, link_id)
    if not link:
        raise NotFoundError("Site link not found")
    _check_owner_or_admin(db, link, user_id)
    if data.group_id is not None:
        if not crud.get_group(db, data.group_id):
            raise NotFoundError("Site group not found")
    link = crud.update_link(db, link, data)
    return _to_link_response(link)


def delete_link(db: Session, link_id: int, user_id: int) -> None:
    link = crud.get_link(db, link_id)
    if not link:
        raise NotFoundError("Site link not found")
    _check_owner_or_admin(db, link, user_id)
    crud.delete_link(db, link)


def _check_owner_or_admin(db: Session, link: SiteLink, user_id: int) -> None:
    user = crud_user.get_user(db, user_id)
    if user and user.role == UserRole.ADMIN:
        return
    if link.created_by != user_id:
        raise ForbiddenError("Only the owner or admin can perform this action")


# ── Manual health check ───────────────────────────────────────────────────────


async def check_link(db: Session, link_id: int) -> SiteCheckResponse:
    link = crud.get_link(db, link_id)
    if not link:
        raise NotFoundError("Site link not found")

    previous_status = link.status
    result = await _perform_check(link.url, link.check_timeout_sec, link.check_ssl_verify)
    checked_at = datetime.now(timezone.utc)
    status_changed = result["status"] != previous_status

    crud.update_link_status(
        db,
        link,
        status=result["status"],
        response_time_ms=result["response_time_ms"],
        http_status_code=result["http_status_code"],
        checked_at=checked_at,
        error_msg=result["error_msg"],
        status_changed=status_changed,
    )

    return SiteCheckResponse(
        id=link.id,
        status=result["status"],
        previous_status=previous_status,
        response_time_ms=result["response_time_ms"],
        http_status_code=result["http_status_code"],
        checked_at=checked_at,
        message=result["message"],
    )


async def _perform_check(url: str, timeout_sec: int, ssl_verify: bool) -> dict:
    """Execute HTTP health check. Returns result dict."""
    start = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(
            verify=ssl_verify,
            timeout=timeout_sec,
            follow_redirects=True,
            max_redirects=SITE_CHECK_MAX_REDIRECTS,
        ) as client:
            try:
                resp = await client.head(url)
                if resp.status_code == 405:
                    resp = await client.get(url)
            except httpx.UnsupportedProtocol:
                # Fallback for protocols that don't support HEAD
                resp = await client.get(url)

        elapsed_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        code = resp.status_code

        if _HTTP_SUCCESS_MIN <= code <= _HTTP_SUCCESS_MAX:
            status = "up"
            message = f"HTTP {code} ({elapsed_ms}ms)"
        else:
            status = "down"
            message = f"HTTP {code}"

        return {
            "status": status,
            "response_time_ms": elapsed_ms if status == "up" else None,
            "http_status_code": code,
            "error_msg": None,
            "message": message,
        }

    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "response_time_ms": None,
            "http_status_code": None,
            "error_msg": f"Timeout after {timeout_sec}s",
            "message": f"Timeout after {timeout_sec}s",
        }
    except Exception as exc:
        err = str(exc)[:_SITE_ERROR_MAX_LENGTH]
        return {
            "status": "error",
            "response_time_ms": None,
            "http_status_code": None,
            "error_msg": err,
            "message": f"Error: {err}",
        }
