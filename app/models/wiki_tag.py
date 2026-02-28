from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import func

from app.database import Base

# Junction table: wiki_pages ↔ wiki_tags (many-to-many)
wiki_page_tags = Table(
    "wiki_page_tags",
    Base.metadata,
    Column("page_id", Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("wiki_tags.id", ondelete="CASCADE"), primary_key=True),
)


class WikiTag(Base):
    __tablename__ = "wiki_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7), nullable=False, server_default="#6c757d")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
