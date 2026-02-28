from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import func

from app.database import Base

# Junction table: wiki_pages ↔ task_list_items (persistent)
wiki_page_task_items = Table(
    "wiki_page_task_items",
    Base.metadata,
    Column("page_id", Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True),
    Column("task_item_id", Integer, ForeignKey("task_list_items.id", ondelete="CASCADE"), primary_key=True),
    Column("linked_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("linked_at", DateTime(timezone=True), server_default=func.now()),
)


class WikiPageTask(Base):
    """wiki_pages ↔ tasks (auxiliary link; task_id SET NULL on task deletion)."""

    __tablename__ = "wiki_page_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    task_title = Column(String(500), nullable=False)  # snapshot at link time
    linked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
