import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import backref, relationship

from app.database import Base
from app.models.wiki_tag import wiki_page_tags
from app.models.wiki_task_link import WikiPageTask, wiki_page_task_items


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True, index=True)
    parent_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=True, server_default="")
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    visibility = Column(String(20), nullable=False, server_default="local")
    category_id = Column(Integer, ForeignKey("wiki_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    search_vector = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at = Column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    # Self-referential parent/children
    children = relationship(
        "WikiPage",
        backref=backref("parent", remote_side=[id]),
        foreign_keys=[parent_id],
        order_by="WikiPage.sort_order",
    )

    author = relationship("User", foreign_keys=[author_id])
    category = relationship("WikiCategory", foreign_keys=[category_id])

    tags = relationship("WikiTag", secondary=wiki_page_tags, lazy="selectin")

    attachments = relationship(
        "WikiAttachment",
        back_populates="page",
        cascade="all, delete-orphan",
        lazy="select",
    )

    linked_task_items = relationship(
        "TaskListItem",
        secondary=wiki_page_task_items,
        lazy="select",
    )

    task_links = relationship(
        "WikiPageTask",
        back_populates="page",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (Index("idx_wiki_pages_search", "search_vector", postgresql_using="gin"),)


# Back-reference on WikiPageTask
WikiPageTask.page = relationship("WikiPage", back_populates="task_links", foreign_keys=[WikiPageTask.page_id])
