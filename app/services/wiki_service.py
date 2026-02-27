"""Business logic for the WIKI feature."""

import logging
import re
import unicodedata
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.constants import WikiPageVisibility
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.crud import wiki_page as page_crud
from app.crud import wiki_tag as tag_crud
from app.crud import wiki_task_link as task_link_crud
from app.models.wiki_page import WikiPage
from app.schemas.wiki import (
    LinkedTaskItemResponse,
    LinkedTaskResponse,
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

logger = logging.getLogger("app.services.wiki")


# ─── Helpers ──────────────────────────────────────────────────────────────────


_SLUG_MAX_BASE_LENGTH = 480  # DB limit is 500; leave room for "-NNN" suffix


def generate_slug(title: str) -> str:
    """Generate a URL slug from a page title."""
    normalized = unicodedata.normalize("NFKC", title)
    slug = re.sub(r"[^\w\s-]", "", normalized.lower())
    slug = re.sub(r"[-\s_]+", "-", slug).strip("-")
    if not slug:
        slug = f"wiki-{str(uuid.uuid4())[:8]}"
    return slug[:_SLUG_MAX_BASE_LENGTH]


def _make_unique_slug(db: Session, base_slug: str, exclude_id: Optional[int] = None) -> str:
    base_slug = base_slug[:_SLUG_MAX_BASE_LENGTH]
    slug = base_slug
    counter = 2
    while page_crud.slug_exists(db, slug, exclude_id=exclude_id):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _extract_text_from_markdown(content: str) -> str:
    """Strip Markdown syntax and return plain text for full-text search indexing."""
    if not content:
        return ""
    # Remove fenced code blocks
    text = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Expand links [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic/strikethrough markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    # Remove blockquote markers
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove task list checkboxes
    text = re.sub(r"^-\s+\[[ x]\]\s+", "- ", text, flags=re.MULTILINE)
    return text.strip()


def _to_page_response(page: WikiPage, db: Session) -> WikiPageResponse:
    author_name = page.author.display_name if page.author else None
    category_name = page.category.name if page.category else None
    category_color = page.category.color if page.category else None
    tags = [WikiTagResponse(id=t.id, name=t.name, slug=t.slug, color=t.color) for t in page.tags]
    return WikiPageResponse(
        id=page.id,
        title=page.title,
        slug=page.slug,
        parent_id=page.parent_id,
        author_id=page.author_id,
        author_name=author_name,
        sort_order=page.sort_order,
        visibility=page.visibility,
        category_id=page.category_id,
        category_name=category_name,
        category_color=category_color,
        tags=tags,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


def _to_detail_response(page: WikiPage, db: Session) -> WikiPageDetailResponse:
    base = _to_page_response(page, db)
    breadcrumbs = page_crud.get_breadcrumbs(db, page.id)
    return WikiPageDetailResponse(
        **base.model_dump(),
        content=page.content or "",
        breadcrumbs=breadcrumbs,
    )


def _require_page(db: Session, page_id: int) -> WikiPage:
    page = page_crud.get_page(db, page_id)
    if not page:
        raise NotFoundError(f"WikiPage {page_id} not found")
    return page


def _check_write_permission(page: WikiPage, user_id: int, is_admin: bool) -> None:
    if not is_admin and page.author_id != user_id:
        raise ForbiddenError("You do not have permission to modify this page")


def _get_user_department_id(db: Session, user_id: int) -> Optional[int]:
    """Return the department_id for the given user, or None."""
    from portal_core.models.user import User as UserModel

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    return user.department_id if user else None


def _check_visibility(page: WikiPage, user_id: int, is_admin: bool, db: Session) -> None:
    """Raise ForbiddenError if user cannot view page.

    Visibility values:
      public  – all authenticated users
      local   – same group as page author (or admin / author themselves)
      private – author or admin only
    """
    if is_admin:
        return
    if page.visibility == WikiPageVisibility.PUBLIC:
        return
    if page.visibility == WikiPageVisibility.LOCAL:
        if page.author_id == user_id:
            return
        # Check if user is in same group as the page author
        if page.author_id is not None:
            from portal_core.models.user import User as UserModel

            author = db.query(UserModel).filter(UserModel.id == page.author_id).first()
            if author and author.department_id is not None:
                user_department_id = _get_user_department_id(db, user_id)
                if user_department_id is not None and user_department_id == author.department_id:
                    return
        raise ForbiddenError("This page is restricted to your department")
    if page.visibility == WikiPageVisibility.PRIVATE:
        if page.author_id == user_id:
            return
        raise ForbiddenError("This page is private")


# ─── Category Service ─────────────────────────────────────────────────────────


def list_categories(db: Session) -> List[WikiCategoryResponse]:
    rows = tag_crud.get_all_categories(db)
    return [
        WikiCategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            color=cat.color,
            sort_order=cat.sort_order,
            page_count=page_count,
        )
        for cat, page_count in rows
    ]


def create_category(db: Session, data: WikiCategoryCreate) -> WikiCategoryResponse:
    if tag_crud.get_category_by_name(db, data.name):
        raise ConflictError(f"Category name '{data.name}' already exists")
    cat = tag_crud.create_category(db, **data.model_dump())
    db.commit()
    return WikiCategoryResponse(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        color=cat.color,
        sort_order=cat.sort_order,
    )


def update_category(db: Session, category_id: int, data: WikiCategoryUpdate) -> WikiCategoryResponse:
    cat = tag_crud.get_category(db, category_id)
    if not cat:
        raise NotFoundError(f"WikiCategory {category_id} not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "name" in updates and updates["name"] != cat.name:
        if tag_crud.get_category_by_name(db, updates["name"]):
            raise ConflictError(f"Category name '{updates['name']}' already exists")
    tag_crud.update_category(db, cat, **updates)
    db.commit()
    return WikiCategoryResponse(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        color=cat.color,
        sort_order=cat.sort_order,
    )


def delete_category(db: Session, category_id: int) -> None:
    cat = tag_crud.get_category(db, category_id)
    if not cat:
        raise NotFoundError(f"WikiCategory {category_id} not found")
    tag_crud.delete_category(db, cat)
    db.commit()


# ─── Tag Service ──────────────────────────────────────────────────────────────


def list_tags(db: Session, q: Optional[str] = None) -> List[WikiTagResponse]:
    rows = tag_crud.get_all_tags(db, q=q)
    return [WikiTagResponse(id=t.id, name=t.name, slug=t.slug, color=t.color, page_count=pc) for t, pc in rows]


def create_tag(db: Session, data: WikiTagCreate, user_id: int) -> WikiTagResponse:
    if tag_crud.get_tag_by_name(db, data.name):
        raise ConflictError(f"Tag '{data.name}' already exists")
    slug = generate_slug(data.name) or f"tag-{str(uuid.uuid4())[:8]}"
    tag = tag_crud.create_tag(db, name=data.name, slug=slug, color=data.color, created_by=user_id)
    db.commit()
    return WikiTagResponse(id=tag.id, name=tag.name, slug=tag.slug, color=tag.color)


def delete_tag(db: Session, tag_id: int) -> None:
    tag = tag_crud.get_tag(db, tag_id)
    if not tag:
        raise NotFoundError(f"WikiTag {tag_id} not found")
    tag_crud.delete_tag(db, tag)
    db.commit()


# ─── Page Service ─────────────────────────────────────────────────────────────


def get_page_tree(db: Session, user_id: int, is_admin: bool = False) -> List[WikiPageTreeNode]:
    user_department_id = _get_user_department_id(db, user_id) if not is_admin else None
    rows = page_crud.get_tree(db, user_id=user_id, user_department_id=user_department_id, is_admin=is_admin)

    def _to_node(d: dict) -> WikiPageTreeNode:
        children = [_to_node(c) for c in d.pop("children", [])]
        return WikiPageTreeNode(
            id=d["id"],
            title=d["title"],
            slug=d["slug"],
            parent_id=d.get("parent_id"),
            author_id=d.get("author_id"),
            author_name=None,
            sort_order=d.get("sort_order", 0),
            visibility=d.get("visibility", "local"),
            category_id=d.get("category_id"),
            category_name=None,
            category_color=None,
            tags=[],
            created_at=d["created_at"],
            updated_at=d.get("updated_at"),
            children=children,
        )

    return [_to_node(r) for r in rows]


def list_pages(
    db: Session,
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> List[WikiPageResponse]:
    user_department_id = _get_user_department_id(db, user_id) if user_id is not None and not is_admin else None
    pages = page_crud.get_all_pages(
        db,
        tag_slug=tag_slug,
        category_id=category_id,
        user_id=user_id,
        user_department_id=user_department_id,
        is_admin=is_admin,
        limit=limit,
        offset=offset,
    )
    return [_to_page_response(p, db) for p in pages]


def get_page_by_id(
    db: Session,
    page_id: int,
    user_id: int,
    is_admin: bool = False,
) -> WikiPageDetailResponse:
    page = _require_page(db, page_id)
    _check_visibility(page, user_id, is_admin, db)
    return _to_detail_response(page, db)


def get_page_by_slug(
    db: Session,
    slug: str,
    user_id: int,
    is_admin: bool = False,
) -> WikiPageDetailResponse:
    page = page_crud.get_page_by_slug(db, slug)
    if not page:
        raise NotFoundError(f"WikiPage with slug '{slug}' not found")
    _check_visibility(page, user_id, is_admin, db)
    return _to_detail_response(page, db)


def create_page(db: Session, data: WikiPageCreate, user_id: int) -> WikiPageDetailResponse:
    base_slug = data.slug or generate_slug(data.title)
    slug = _make_unique_slug(db, base_slug)

    content = data.content or ""
    page = page_crud.create_page(
        db,
        title=data.title,
        slug=slug,
        parent_id=data.parent_id,
        content=content,
        author_id=user_id,
        sort_order=data.sort_order,
        visibility=data.visibility,
        category_id=data.category_id,
        tag_ids=data.tag_ids,
    )
    # Update full-text search vector immediately on creation
    body_text = _extract_text_from_markdown(content)
    page_crud.update_search_vector(db, page.id, f"{data.title} {body_text}")
    db.commit()
    db.refresh(page)
    return _to_detail_response(page, db)


def update_page(
    db: Session,
    page_id: int,
    data: WikiPageUpdate,
    user_id: int,
    is_admin: bool,
) -> WikiPageDetailResponse:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)

    updates: dict = {}
    if data.title is not None:
        updates["title"] = data.title
    if data.slug is not None:
        new_slug = _make_unique_slug(db, data.slug, exclude_id=page_id)
        updates["slug"] = new_slug
    if data.content is not None:
        updates["content"] = data.content
    if data.sort_order is not None:
        updates["sort_order"] = data.sort_order
    if data.visibility is not None:
        updates["visibility"] = data.visibility
    if data.category_id is not None or "category_id" in data.model_fields_set:
        updates["category_id"] = data.category_id

    page_crud.update_page(db, page, **updates)

    # Update search vector from Tiptap content
    body_text = _extract_text_from_markdown(page.content or "")
    page_crud.update_search_vector(db, page.id, f"{page.title} {body_text}")

    db.commit()
    db.refresh(page)
    return _to_detail_response(page, db)


def delete_page(db: Session, page_id: int, user_id: int, is_admin: bool) -> None:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)
    page_crud.delete_page(db, page)
    db.commit()


def move_page(
    db: Session,
    page_id: int,
    data: WikiPageMove,
    user_id: int,
    is_admin: bool,
) -> WikiPageDetailResponse:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)

    if data.parent_id is not None:
        if data.parent_id == page_id:
            raise ConflictError("A page cannot be its own parent")
        if page_crud.is_descendant(db, page_id, data.parent_id):
            raise ConflictError("Circular reference: the target parent is a descendant of this page")

    updates: dict = {}
    if "parent_id" in data.model_fields_set:
        updates["parent_id"] = data.parent_id
    if data.sort_order is not None:
        updates["sort_order"] = data.sort_order

    page_crud.update_page(db, page, **updates)
    db.commit()
    db.refresh(page)
    return _to_detail_response(page, db)


def update_page_tags(
    db: Session,
    page_id: int,
    data: WikiTagIdsUpdate,
    user_id: int,
    is_admin: bool,
) -> WikiPageResponse:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)
    tag_crud.update_page_tags(db, page, data.tag_ids)
    db.commit()
    db.refresh(page)
    return _to_page_response(page, db)


# ─── Task Link Service ────────────────────────────────────────────────────────


def get_task_links(db: Session, page_id: int) -> WikiTaskLinksResponse:
    _require_page(db, page_id)
    task_item_rows, task_rows = task_link_crud.get_task_links(db, page_id)

    task_items = [
        LinkedTaskItemResponse(
            id=r.id,
            title=r.title,
            status=r.status,
            assignee_id=r.assignee_id,
            assignee_name=r.assignee_name,
            backlog_ticket_id=r.backlog_ticket_id,
            scheduled_date=r.scheduled_date,
            linked_at=r.linked_at,
        )
        for r in task_item_rows
    ]

    tasks = [
        LinkedTaskResponse(
            link_id=r.link_id,
            task_id=r.task_id,
            title=r.task_title,
            status=r.status,
            user_id=r.user_id,
            display_name=r.display_name,
            backlog_ticket_id=r.backlog_ticket_id,
            is_completed=r.task_id is None,
            linked_at=r.linked_at,
        )
        for r in task_rows
    ]

    return WikiTaskLinksResponse(task_items=task_items, tasks=tasks)


def update_task_item_links(
    db: Session,
    page_id: int,
    data: WikiTaskItemLinksUpdate,
    user_id: int,
    is_admin: bool = False,
) -> WikiTaskLinksResponse:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)
    task_link_crud.update_task_item_links(db, page_id, data.task_item_ids, user_id)
    db.commit()
    return get_task_links(db, page_id)


def add_task_link(db: Session, page_id: int, task_id: int, user_id: int, is_admin: bool = False) -> None:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)
    result = task_link_crud.add_task_link(db, page_id, task_id, user_id)
    if result is None:
        raise NotFoundError(f"Task {task_id} not found")
    db.commit()


def remove_task_link(db: Session, page_id: int, task_id: int, user_id: int, is_admin: bool = False) -> None:
    page = _require_page(db, page_id)
    _check_write_permission(page, user_id, is_admin)
    removed = task_link_crud.remove_task_link(db, page_id, task_id)
    if not removed:
        raise NotFoundError(f"Task link for task {task_id} on page {page_id} not found")
    db.commit()
