from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.task_category import TaskCategory
from app.schemas.task_category import TaskCategoryCreate, TaskCategoryUpdate

_crud = CRUDBase(TaskCategory)


def get_all_categories(db: Session) -> List[TaskCategory]:
    return db.query(TaskCategory).order_by(TaskCategory.id).all()


get_category = _crud.get


def create_category(db: Session, data: TaskCategoryCreate) -> TaskCategory:
    return _crud.create(db, data)


def update_category(db: Session, category: TaskCategory, data: TaskCategoryUpdate) -> TaskCategory:
    return _crud.update(db, category, data)


delete_category = _crud.delete
