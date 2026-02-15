from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate


def get_todos(db: Session, user_id: int) -> List[Todo]:
    return db.query(Todo).filter(Todo.user_id == user_id).order_by(Todo.priority.desc(), Todo.created_at.desc()).all()


def get_todo(db: Session, todo_id: int) -> Optional[Todo]:
    return db.query(Todo).filter(Todo.id == todo_id).first()


def create_todo(db: Session, user_id: int, data: TodoCreate) -> Todo:
    todo = Todo(user_id=user_id, **data.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(db: Session, todo: Todo, data: TodoUpdate) -> Todo:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    db.delete(todo)
    db.commit()


def toggle_todo(db: Session, todo: Todo) -> Todo:
    todo.is_completed = not todo.is_completed
    db.commit()
    db.refresh(todo)
    return todo


def get_public_todos(db: Session) -> List[Todo]:
    return (
        db.query(Todo).filter(Todo.visibility == "public").order_by(Todo.priority.desc(), Todo.created_at.desc()).all()
    )
