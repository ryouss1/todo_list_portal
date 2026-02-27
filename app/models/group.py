from sqlalchemy import Column, DateTime, Integer, String, func

from portal_core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
