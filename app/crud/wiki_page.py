"""CRUD operations for WikiPage."""

from typing import List, Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session, joinedload, noload

from app.constants import WikiPageVisibility
from app.models.wiki_page import WikiPage
from app.models.wiki_tag import WikiTag


def get_page(db: Session, page_id: int) -> Optional[WikiPage]:
    return db.query(WikiPage).filter(WikiPage.id == page_id).first()


def get_page_by_slug(db: Session, slug: str) -> Optional[WikiPage]:
    return db.query(WikiPage).filter(WikiPage.slug == slug).first()


def get_all_pages(
    db: Session,
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_group_id: Optional[int] = None,
    is_admin: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> List[WikiPage]:
    query = db.query(WikiPage).options(
        joinedload(WikiPage.author),
        joinedload(WikiPage.category),
        noload(WikiPage.linked_task_items),
        noload(WikiPage.task_links),
        noload(WikiPage.attachments),
    )
    # Visibility filter:
    #   public  → all authenticated users
    #   local   → same group as author (or the author themselves)
    #   private → author only
    if not is_admin:
        if user_id is not None:
            public_cond = WikiPage.visibility == WikiPageVisibility.PUBLIC
            private_cond = and_(
                WikiPage.visibility == WikiPageVisibility.PRIVATE,
                WikiPage.author_id == user_id,
            )
            # local: visible if user is the author OR user is in same group as author
            local_subconditions = [WikiPage.author_id == user_id]
            if user_group_id is not None:
                from portal_core.models.user import User as UserModel

                same_group_authors = db.query(UserModel.id).filter(UserModel.department_id == user_group_id)
                local_subconditions.append(WikiPage.author_id.in_(same_group_authors))
            local_cond = and_(
                WikiPage.visibility == WikiPageVisibility.LOCAL,
                or_(*local_subconditions),
            )
            query = query.filter(or_(public_cond, local_cond, private_cond))
        else:
            # unauthenticated: no pages visible (all visibility values require auth now)
            query = query.filter(WikiPage.id < 0)  # returns nothing
    if tag_slug:
        from app.models.wiki_tag import WikiTag, wiki_page_tags

        query = (
            query.join(wiki_page_tags, WikiPage.id == wiki_page_tags.c.page_id)
            .join(WikiTag, WikiTag.id == wiki_page_tags.c.tag_id)
            .filter(WikiTag.slug == tag_slug)
        )
    if category_id is not None:
        query = query.filter(WikiPage.category_id == category_id)
    return query.order_by(WikiPage.sort_order, WikiPage.id).limit(limit).offset(offset).all()


def create_page(db: Session, **kwargs) -> WikiPage:
    tag_ids = kwargs.pop("tag_ids", None)
    page = WikiPage(**kwargs)
    db.add(page)
    db.flush()
    if tag_ids:
        tags = db.query(WikiTag).filter(WikiTag.id.in_(tag_ids)).all()
        page.tags = tags
        db.flush()
    return page


def update_page(db: Session, page: WikiPage, **kwargs) -> WikiPage:
    for key, val in kwargs.items():
        setattr(page, key, val)
    db.flush()
    return page


def delete_page(db: Session, page: WikiPage) -> None:
    # Children: SET NULL is handled by DB FK; orphaned children become root pages
    db.delete(page)
    db.flush()


def get_tree(
    db: Session,
    user_id: int,
    user_group_id: Optional[int] = None,
    is_admin: bool = False,
) -> List[dict]:
    """Return pages as a nested tree using a recursive CTE, filtered by visibility."""
    rows = db.execute(
        text("""
            WITH RECURSIVE tree AS (
                SELECT id, title, slug, parent_id, sort_order, visibility,
                       author_id, category_id, created_at, updated_at, 0 AS depth
                FROM wiki_pages
                WHERE parent_id IS NULL
                  AND (
                    :is_admin = true
                    OR visibility = 'public'
                    OR (
                        visibility = 'local' AND (
                            author_id = :user_id
                            OR (
                                :user_group_id IS NOT NULL
                                AND author_id IN (
                                    SELECT id FROM users WHERE department_id = :user_group_id
                                )
                            )
                        )
                    )
                    OR (visibility = 'private' AND author_id = :user_id)
                  )

                UNION ALL

                SELECT wp.id, wp.title, wp.slug, wp.parent_id, wp.sort_order,
                       wp.visibility, wp.author_id, wp.category_id,
                       wp.created_at, wp.updated_at, tree.depth + 1
                FROM wiki_pages wp
                INNER JOIN tree ON wp.parent_id = tree.id
                WHERE (
                    :is_admin = true
                    OR wp.visibility = 'public'
                    OR (
                        wp.visibility = 'local' AND (
                            wp.author_id = :user_id
                            OR (
                                :user_group_id IS NOT NULL
                                AND wp.author_id IN (
                                    SELECT id FROM users WHERE department_id = :user_group_id
                                )
                            )
                        )
                    )
                    OR (wp.visibility = 'private' AND wp.author_id = :user_id)
                )
            )
            SELECT * FROM tree ORDER BY depth, sort_order, id
        """),
        {"user_id": user_id, "user_group_id": user_group_id, "is_admin": is_admin},
    ).fetchall()
    return _build_tree(rows)


def _build_tree(rows: list) -> list:
    node_map: dict = {}
    roots: list = []
    for row in rows:
        node = dict(row._mapping)
        node["children"] = []
        node_map[node["id"]] = node
        if node["parent_id"] is None:
            roots.append(node)
        else:
            parent = node_map.get(node["parent_id"])
            if parent:
                parent["children"].append(node)
    return roots


def get_breadcrumbs(db: Session, page_id: int) -> list:
    """Return ordered ancestor path from root to parent (excludes the page itself)."""
    result = db.execute(
        text("""
            WITH RECURSIVE ancestors AS (
                SELECT id, title, slug, parent_id, 0 AS depth
                FROM wiki_pages WHERE id = :page_id
                UNION ALL
                SELECT wp.id, wp.title, wp.slug, wp.parent_id, a.depth + 1
                FROM wiki_pages wp
                INNER JOIN ancestors a ON wp.id = a.parent_id
            )
            SELECT id, title, slug FROM ancestors
            WHERE id != :page_id
            ORDER BY depth DESC
        """),
        {"page_id": page_id},
    ).fetchall()
    return [{"id": r.id, "title": r.title, "slug": r.slug} for r in result]


def is_descendant(db: Session, ancestor_id: int, candidate_id: int) -> bool:
    """Return True if candidate_id is a descendant of ancestor_id."""
    result = db.execute(
        text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM wiki_pages WHERE id = :ancestor_id
                UNION ALL
                SELECT wp.id FROM wiki_pages wp
                INNER JOIN descendants d ON wp.parent_id = d.id
            )
            SELECT 1 FROM descendants WHERE id = :candidate_id
        """),
        {"ancestor_id": ancestor_id, "candidate_id": candidate_id},
    ).fetchone()
    return result is not None


def slug_exists(db: Session, slug: str, exclude_id: Optional[int] = None) -> bool:
    query = db.query(WikiPage).filter(WikiPage.slug == slug)
    if exclude_id:
        query = query.filter(WikiPage.id != exclude_id)
    return query.first() is not None


def update_search_vector(db: Session, page_id: int, text_content: str) -> None:
    """Update search_vector with extracted text from Tiptap JSON content."""
    db.execute(
        text("""
            UPDATE wiki_pages
            SET search_vector = to_tsvector('pg_catalog.simple', :title || ' ' || :body)
            WHERE id = :page_id
        """),
        {"page_id": page_id, "title": text_content, "body": text_content},
    )
