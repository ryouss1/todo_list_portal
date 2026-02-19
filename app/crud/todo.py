from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

_crud = CRUDBase(Todo)

get_todo = _crud.get


def get_todos(db: Session, user_id: int) -> List[Todo]:
    return db.query(Todo).filter(Todo.user_id == user_id).order_by(Todo.priority.desc(), Todo.created_at.desc()).all()


def create_todo(db: Session, user_id: int, data: TodoCreate) -> Todo:
    return _crud.create(db, data, user_id=user_id)


def update_todo(db: Session, todo: Todo, data: TodoUpdate) -> Todo:
    return _crud.update(db, todo, data)


delete_todo = _crud.delete


def toggle_todo(db: Session, todo: Todo) -> Todo:
    todo.is_completed = not todo.is_completed
    db.commit()
    db.refresh(todo)
    return todo


def get_public_todos(db: Session) -> List[Todo]:
    return (
        db.query(Todo).filter(Todo.visibility == "public").order_by(Todo.priority.desc(), Todo.created_at.desc()).all()
    )
