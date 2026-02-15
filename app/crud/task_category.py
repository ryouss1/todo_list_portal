from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.task_category import TaskCategory
from app.schemas.task_category import TaskCategoryCreate, TaskCategoryUpdate


def get_all_categories(db: Session) -> List[TaskCategory]:
    return db.query(TaskCategory).order_by(TaskCategory.id).all()


def get_category(db: Session, category_id: int) -> Optional[TaskCategory]:
    return db.query(TaskCategory).filter(TaskCategory.id == category_id).first()


def create_category(db: Session, data: TaskCategoryCreate) -> TaskCategory:
    category = TaskCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: TaskCategory, data: TaskCategoryUpdate) -> TaskCategory:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: TaskCategory) -> None:
    db.delete(category)
    db.commit()
