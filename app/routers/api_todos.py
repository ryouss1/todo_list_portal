from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from app.services import todo_service as svc_todo

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get("/", response_model=List[TodoResponse])
def list_todos(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_todo.list_todos(db, user_id)


@router.post("/", response_model=TodoResponse, status_code=201)
def create_todo(data: TodoCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_todo.create_todo(db, user_id, data)


@router.get("/public", response_model=List[TodoResponse])
def list_public_todos(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_todo.list_public_todos(db)


@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_todo.get_todo(db, todo_id, user_id)


@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: int, data: TodoUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    return svc_todo.update_todo(db, todo_id, user_id, data)


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    svc_todo.delete_todo(db, todo_id, user_id)


@router.patch("/{todo_id}/toggle", response_model=TodoResponse)
def toggle_todo(todo_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_todo.toggle_todo(db, todo_id, user_id)
