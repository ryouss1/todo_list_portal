import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.crud import todo as crud_todo
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

logger = logging.getLogger("app.services.todo")


def list_todos(db: Session, user_id: int) -> List[Todo]:
    logger.info("Listing todos for user_id=%d", user_id)
    return crud_todo.get_todos(db, user_id)


def get_todo(db: Session, todo_id: int, user_id: int) -> Todo:
    todo = crud_todo.get_todo(db, todo_id)
    if not todo or todo.user_id != user_id:
        logger.warning("Todo not found: id=%d", todo_id)
        raise NotFoundError("Todo not found")
    return todo


def create_todo(db: Session, user_id: int, data: TodoCreate) -> Todo:
    logger.info("Creating todo: title=%s, priority=%d", data.title, data.priority)
    todo = crud_todo.create_todo(db, user_id, data)
    logger.info("Todo created: id=%d", todo.id)
    return todo


def update_todo(db: Session, todo_id: int, user_id: int, data: TodoUpdate) -> Todo:
    todo = get_todo(db, todo_id, user_id)
    logger.info("Updating todo: id=%d", todo_id)
    return crud_todo.update_todo(db, todo, data)


def delete_todo(db: Session, todo_id: int, user_id: int) -> None:
    todo = get_todo(db, todo_id, user_id)
    crud_todo.delete_todo(db, todo)
    logger.info("Todo deleted: id=%d", todo_id)


def toggle_todo(db: Session, todo_id: int, user_id: int) -> Todo:
    todo = get_todo(db, todo_id, user_id)
    result = crud_todo.toggle_todo(db, todo)
    logger.info("Todo toggled: id=%d, is_completed=%s", todo_id, result.is_completed)
    return result


def list_public_todos(db: Session) -> List[Todo]:
    logger.info("Listing public todos")
    return crud_todo.get_public_todos(db)
