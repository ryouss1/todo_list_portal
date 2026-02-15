from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.task_category import TaskCategoryCreate, TaskCategoryResponse, TaskCategoryUpdate
from app.services import task_category_service as svc

router = APIRouter(prefix="/api/task-categories", tags=["task-categories"])


@router.get("/", response_model=List[TaskCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_categories(db)


@router.post("/", response_model=TaskCategoryResponse, status_code=201)
def create_category(
    data: TaskCategoryCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.create_category(db, data)


@router.put("/{category_id}", response_model=TaskCategoryResponse)
def update_category(
    category_id: int,
    data: TaskCategoryUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_category(db, category_id)
