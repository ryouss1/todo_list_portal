"""CRUD operations for SiteGroup and SiteLink."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.site_link import SiteGroup, SiteLink
from app.schemas.site_link import SiteGroupCreate, SiteGroupUpdate, SiteLinkCreate, SiteLinkUpdate

# ── SiteGroup ───────────────────────────────────────────────────────────────


def get_groups(db: Session) -> List[SiteGroup]:
    return db.query(SiteGroup).order_by(SiteGroup.sort_order, SiteGroup.name).all()


def get_group(db: Session, group_id: int) -> Optional[SiteGroup]:
    return db.query(SiteGroup).filter(SiteGroup.id == group_id).first()


def get_group_by_name(db: Session, name: str) -> Optional[SiteGroup]:
    return db.query(SiteGroup).filter(SiteGroup.name == name).first()


def create_group(db: Session, data: SiteGroupCreate) -> SiteGroup:
    group = SiteGroup(
        name=data.name,
        description=data.description,
        color=data.color,
        icon=data.icon,
        sort_order=data.sort_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, group: SiteGroup, data: SiteGroupUpdate) -> SiteGroup:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group: SiteGroup) -> None:
    db.delete(group)
    db.commit()


def count_links_by_group(db: Session, group_id: int) -> int:
    return db.query(func.count(SiteLink.id)).filter(SiteLink.group_id == group_id).scalar() or 0


def count_links_all_groups(db: Session) -> Dict[Optional[int], int]:
    """Return {group_id: count} for all groups in a single query."""
    rows = db.query(SiteLink.group_id, func.count(SiteLink.id)).group_by(SiteLink.group_id).all()
    return {gid: cnt for gid, cnt in rows}


# ── SiteLink ─────────────────────────────────────────────────────────────────


def get_links(db: Session) -> List[SiteLink]:
    return (
        db.query(SiteLink)
        .filter(SiteLink.is_enabled == True)  # noqa: E712
        .order_by(SiteLink.group_id.nullsfirst(), SiteLink.sort_order, SiteLink.name)
        .all()
    )


def get_all_links(db: Session) -> List[SiteLink]:
    """Return all links regardless of is_enabled (for background checker)."""
    return (
        db.query(SiteLink)
        .filter(SiteLink.is_enabled == True, SiteLink.check_enabled == True)  # noqa: E712
        .all()
    )


def get_link(db: Session, link_id: int) -> Optional[SiteLink]:
    return db.query(SiteLink).filter(SiteLink.id == link_id).first()


def create_link(db: Session, data: SiteLinkCreate, user_id: int) -> SiteLink:
    link = SiteLink(
        name=data.name,
        url=data.url,
        description=data.description,
        group_id=data.group_id,
        created_by=user_id,
        sort_order=data.sort_order,
        is_enabled=data.is_enabled,
        check_enabled=data.check_enabled,
        check_interval_sec=data.check_interval_sec,
        check_timeout_sec=data.check_timeout_sec,
        check_ssl_verify=data.check_ssl_verify,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def update_link(db: Session, link: SiteLink, data: SiteLinkUpdate) -> SiteLink:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(link, field, value)
    db.commit()
    db.refresh(link)
    return link


def delete_link(db: Session, link: SiteLink) -> None:
    db.delete(link)
    db.commit()


def update_link_status(
    db: Session,
    link: SiteLink,
    status: str,
    response_time_ms: Optional[int],
    http_status_code: Optional[int],
    checked_at: datetime,
    error_msg: Optional[str],
    status_changed: bool,
) -> SiteLink:
    link.status = status
    link.response_time_ms = response_time_ms
    link.http_status_code = http_status_code
    link.last_checked_at = checked_at
    link.last_error = error_msg
    if status in ("up", "unknown"):
        link.consecutive_failures = 0
    else:
        link.consecutive_failures = (link.consecutive_failures or 0) + 1
    if status_changed:
        link.last_status_changed_at = checked_at
    db.commit()
    db.refresh(link)
    return link
