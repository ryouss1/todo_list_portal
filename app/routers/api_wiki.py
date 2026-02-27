"""WIKI API router."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.wiki import (
    WikiCategoryCreate,
    WikiCategoryResponse,
    WikiCategoryUpdate,
    WikiPageCreate,
    WikiPageDetailResponse,
    WikiPageMove,
    WikiPageResponse,
    WikiPageTreeNode,
    WikiPageUpdate,
    WikiTagCreate,
    WikiTagIdsUpdate,
    WikiTagResponse,
    WikiTaskItemLinksUpdate,
    WikiTaskLinksResponse,
)
from app.services import wiki_service as svc

# ─── Category router ──────────────────────────────────────────────────────────

category_router = APIRouter(prefix="/api/wiki/categories", tags=["wiki-categories"])


@category_router.get("/", response_model=List[WikiCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_categories(db)


@category_router.post("/", response_model=WikiCategoryResponse, status_code=201)
def create_category(
    data: WikiCategoryCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.create_category(db, data)


@category_router.put("/{category_id}", response_model=WikiCategoryResponse)
def update_category(
    category_id: int,
    data: WikiCategoryUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.update_category(db, category_id, data)


@category_router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_category(db, category_id)


# ─── Tag router ───────────────────────────────────────────────────────────────

tag_router = APIRouter(prefix="/api/wiki/tags", tags=["wiki-tags"])


@tag_router.get("/", response_model=List[WikiTagResponse])
def list_tags(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_tags(db, q=q)


@tag_router.post("/", response_model=WikiTagResponse, status_code=201)
def create_tag(
    data: WikiTagCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_tag(db, data, user_id)


@tag_router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_tag(db, tag_id)


# ─── Page router ──────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/wiki/pages", tags=["wiki"])


@router.get("/tree", response_model=List[WikiPageTreeNode])
def get_page_tree(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_page_tree(db, user_id=user_id)


@router.get("/by-slug/{slug}", response_model=WikiPageDetailResponse)
def get_page_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_page_by_slug(db, slug, user_id=user_id, is_admin=False)


@router.get("/", response_model=List[WikiPageResponse])
def list_pages(
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_pages(db, tag_slug=tag_slug, category_id=category_id, user_id=user_id, limit=limit, offset=offset)


@router.post("/", response_model=WikiPageDetailResponse, status_code=201)
def create_page(
    data: WikiPageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_page(db, data, user_id)


@router.get("/{page_id}", response_model=WikiPageDetailResponse)
def get_page(
    page_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_page_by_id(db, page_id, user_id=user_id, is_admin=False)


@router.put("/{page_id}", response_model=WikiPageDetailResponse)
def update_page(
    page_id: int,
    data: WikiPageUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_page(db, page_id, data, user_id, is_admin=False)


@router.delete("/{page_id}", status_code=204)
def delete_page(
    page_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.delete_page(db, page_id, user_id, is_admin=False)


@router.put("/{page_id}/move", response_model=WikiPageDetailResponse)
def move_page(
    page_id: int,
    data: WikiPageMove,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.move_page(db, page_id, data, user_id, is_admin=False)


@router.put("/{page_id}/tags", response_model=WikiPageResponse)
def update_page_tags(
    page_id: int,
    data: WikiTagIdsUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_page_tags(db, page_id, data, user_id, is_admin=False)


# ─── Task link sub-endpoints ──────────────────────────────────────────────────


@router.get("/{page_id}/tasks", response_model=WikiTaskLinksResponse)
def get_task_links(
    page_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_task_links(db, page_id)


@router.put("/{page_id}/tasks/task-items", response_model=WikiTaskLinksResponse)
def update_task_item_links(
    page_id: int,
    data: WikiTaskItemLinksUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_task_item_links(db, page_id, data, user_id)


@router.post("/{page_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_task_link(
    page_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.add_task_link(db, page_id, task_id, user_id)


@router.delete("/{page_id}/tasks/{task_id}", status_code=204)
def remove_task_link(
    page_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.remove_task_link(db, page_id, task_id, user_id)
