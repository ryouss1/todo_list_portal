"""CRUD operations for WikiCategory and WikiTag."""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.wiki_category import WikiCategory
from app.models.wiki_page import WikiPage
from app.models.wiki_tag import WikiTag, wiki_page_tags

# ─── WikiCategory ─────────────────────────────────────────────────────────────


def get_all_categories(db: Session) -> List:
    return (
        db.query(WikiCategory, func.count(WikiPage.id).label("page_count"))
        .outerjoin(WikiPage, WikiPage.category_id == WikiCategory.id)
        .group_by(WikiCategory.id)
        .order_by(WikiCategory.sort_order, WikiCategory.id)
        .all()
    )


def get_category(db: Session, category_id: int) -> Optional[WikiCategory]:
    return db.query(WikiCategory).filter(WikiCategory.id == category_id).first()


def get_category_by_name(db: Session, name: str) -> Optional[WikiCategory]:
    return db.query(WikiCategory).filter(WikiCategory.name == name).first()


def create_category(db: Session, **kwargs) -> WikiCategory:
    cat = WikiCategory(**kwargs)
    db.add(cat)
    db.flush()
    return cat


def update_category(db: Session, cat: WikiCategory, **kwargs) -> WikiCategory:
    for key, val in kwargs.items():
        setattr(cat, key, val)
    db.flush()
    return cat


def delete_category(db: Session, cat: WikiCategory) -> None:
    db.delete(cat)
    db.flush()


# ─── WikiTag ──────────────────────────────────────────────────────────────────


def get_all_tags(db: Session, q: Optional[str] = None) -> List:
    query = db.query(WikiTag, func.count(wiki_page_tags.c.page_id).label("page_count")).outerjoin(
        wiki_page_tags, WikiTag.id == wiki_page_tags.c.tag_id
    )
    if q:
        query = query.filter(WikiTag.name.ilike(f"%{q}%"))
    return query.group_by(WikiTag.id).order_by(WikiTag.name).all()


def get_tag(db: Session, tag_id: int) -> Optional[WikiTag]:
    return db.query(WikiTag).filter(WikiTag.id == tag_id).first()


def get_tag_by_name(db: Session, name: str) -> Optional[WikiTag]:
    return db.query(WikiTag).filter(WikiTag.name == name).first()


def create_tag(db: Session, **kwargs) -> WikiTag:
    tag = WikiTag(**kwargs)
    db.add(tag)
    db.flush()
    return tag


def delete_tag(db: Session, tag: WikiTag) -> None:
    db.delete(tag)
    db.flush()


def update_page_tags(db: Session, page: WikiPage, tag_ids: List[int]) -> WikiPage:
    tags = db.query(WikiTag).filter(WikiTag.id.in_(tag_ids)).all()
    page.tags = tags
    db.flush()
    return page
