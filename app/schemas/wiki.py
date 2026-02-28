"""Pydantic schemas for WIKI feature."""

from datetime import date, datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field

from app.constants import WikiPageVisibility

# Validated hex color string: must be exactly #RRGGBB
_ColorHex = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]

# ─── WikiCategory ─────────────────────────────────────────────────────────────


class WikiCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: _ColorHex = "#6c757d"
    sort_order: int = 0


class WikiCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[_ColorHex] = None
    sort_order: Optional[int] = None


class WikiCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: str
    sort_order: int
    page_count: int = 0

    class Config:
        from_attributes = True


# ─── WikiTag ──────────────────────────────────────────────────────────────────


class WikiTagCreate(BaseModel):
    name: str
    color: _ColorHex = "#6c757d"


class WikiTagResponse(BaseModel):
    id: int
    name: str
    slug: str
    color: str
    page_count: int = 0

    class Config:
        from_attributes = True


# ─── WikiPage ─────────────────────────────────────────────────────────────────


class WikiBreadcrumb(BaseModel):
    id: int
    title: str
    slug: str


class WikiPageCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    parent_id: Optional[int] = None
    content: Optional[str] = None
    sort_order: int = 0
    visibility: str = WikiPageVisibility.LOCAL
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class WikiPageUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    sort_order: Optional[int] = None
    visibility: Optional[str] = None
    category_id: Optional[int] = None


class WikiPageMove(BaseModel):
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class WikiTagIdsUpdate(BaseModel):
    tag_ids: List[int]


class WikiPageResponse(BaseModel):
    id: int
    title: str
    slug: str
    parent_id: Optional[int]
    author_id: Optional[int]
    author_name: Optional[str]
    sort_order: int
    visibility: str
    category_id: Optional[int]
    category_name: Optional[str]
    category_color: Optional[str]
    tags: List[WikiTagResponse] = []
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class WikiPageDetailResponse(WikiPageResponse):
    content: str
    breadcrumbs: List[WikiBreadcrumb] = []


class WikiPageTreeNode(WikiPageResponse):
    children: List["WikiPageTreeNode"] = []


WikiPageTreeNode.model_rebuild()


# ─── WikiTaskLinks ────────────────────────────────────────────────────────────


class LinkedTaskItemResponse(BaseModel):
    id: int
    title: str
    status: str
    assignee_id: Optional[int]
    assignee_name: Optional[str]
    backlog_ticket_id: Optional[str]
    scheduled_date: Optional[date]
    linked_at: datetime

    class Config:
        from_attributes = True


class LinkedTaskResponse(BaseModel):
    link_id: int
    task_id: Optional[int]
    title: str  # task_title snapshot
    status: Optional[str]
    user_id: Optional[int]
    display_name: Optional[str]
    backlog_ticket_id: Optional[str]
    is_completed: bool  # True when task_id is None
    linked_at: datetime

    class Config:
        from_attributes = True


class WikiTaskLinksResponse(BaseModel):
    task_items: List[LinkedTaskItemResponse]
    tasks: List[LinkedTaskResponse]


class WikiTaskItemLinksUpdate(BaseModel):
    task_item_ids: List[int]
