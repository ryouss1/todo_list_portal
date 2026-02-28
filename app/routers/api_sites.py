from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
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
from app.services import site_link_service as svc

router = APIRouter(prefix="/api/sites", tags=["sites"])
group_router = APIRouter(prefix="/api/site-groups", tags=["site-groups"])


# ── SiteGroup endpoints ──────────────────────────────────────────────────────


@group_router.get("/", response_model=List[SiteGroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_groups(db)


@group_router.post("/", response_model=SiteGroupResponse, status_code=201)
def create_group(
    data: SiteGroupCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.create_group(db, data)


@group_router.put("/{group_id}", response_model=SiteGroupResponse)
def update_group(
    group_id: int,
    data: SiteGroupUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.update_group(db, group_id, data)


@group_router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_group(db, group_id)


# ── SiteLink endpoints ───────────────────────────────────────────────────────


@router.get("/", response_model=List[SiteLinkResponse])
def list_links(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_links(db)


@router.post("/", response_model=SiteLinkResponse, status_code=201)
def create_link(
    data: SiteLinkCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_link(db, data, user_id)


@router.get("/{link_id}", response_model=SiteLinkResponse)
def get_link(
    link_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_link(db, link_id)


@router.get("/{link_id}/url", response_model=SiteUrlResponse)
def get_link_url(
    link_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_link_url(db, link_id, user_id)


@router.put("/{link_id}", response_model=SiteLinkResponse)
def update_link(
    link_id: int,
    data: SiteLinkUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_link(db, link_id, data, user_id)


@router.delete("/{link_id}", status_code=204)
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.delete_link(db, link_id, user_id)


@router.post("/{link_id}/check", response_model=SiteCheckResponse)
async def check_link(
    link_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return await svc.check_link(db, link_id)
