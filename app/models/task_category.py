from sqlalchemy import Column, Integer, String

from app.database import Base


class TaskCategory(Base):
    __tablename__ = "task_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
