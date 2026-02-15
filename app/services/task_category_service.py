import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.crud import task_category as crud_category
from app.models.task_category import TaskCategory
from app.schemas.task_category import TaskCategoryCreate, TaskCategoryUpdate

logger = logging.getLogger("app.services.task_category")


def list_categories(db: Session) -> List[TaskCategory]:
    return crud_category.get_all_categories(db)


def get_category(db: Session, category_id: int) -> TaskCategory:
    category = crud_category.get_category(db, category_id)
    if not category:
        raise NotFoundError("Task category not found")
    return category


def create_category(db: Session, data: TaskCategoryCreate) -> TaskCategory:
    logger.info("Creating task category: name=%s", data.name)
    return crud_category.create_category(db, data)


def update_category(db: Session, category_id: int, data: TaskCategoryUpdate) -> TaskCategory:
    category = get_category(db, category_id)
    logger.info("Updating task category: id=%d", category_id)
    return crud_category.update_category(db, category, data)


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    logger.info("Deleting task category: id=%d", category_id)
    crud_category.delete_category(db, category)
