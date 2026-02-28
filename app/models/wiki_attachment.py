"""WikiAttachment model — stores file metadata for WIKI page attachments.

Physical files are stored under: uploads/wiki/{page_id}/{stored_filename}

The `after_delete` SQLAlchemy event listener automatically removes the physical
file from disk when a WikiAttachment record is deleted.  This ensures no orphaned
files accumulate even when wiki_pages are CASCADE-deleted.
"""

import logging
import os

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import relationship

from app.database import Base

logger = logging.getLogger("app.models.wiki_attachment")


class WikiAttachment(Base):
    __tablename__ = "wiki_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(
        Integer,
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(500), nullable=False)  # display name (original)
    stored_path = Column(String(1000), nullable=False)  # relative path on disk
    mime_type = Column(String(200), nullable=True)
    file_size = Column(Integer, nullable=False, server_default="0")  # bytes
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now())

    page = relationship("WikiPage", back_populates="attachments")

    __table_args__ = (Index("idx_wiki_attachments_page_id", "page_id"),)


# ─── Physical-file cleanup on delete ─────────────────────────────────────────


@event.listens_for(WikiAttachment, "after_delete")
def _delete_physical_file(mapper, connection, target: "WikiAttachment") -> None:
    """Remove the physical file from disk after the DB record is deleted.

    Called automatically by SQLAlchemy for both direct deletes and CASCADE
    deletes triggered by the parent wiki_page being removed.
    """
    path = target.stored_path
    if not path:
        return
    if os.path.isfile(path):
        try:
            os.remove(path)
            logger.info("Deleted attachment file: %s", path)
        except OSError:
            logger.warning("Failed to delete attachment file: %s", path, exc_info=True)
    else:
        logger.debug("Attachment file already absent (skip): %s", path)
