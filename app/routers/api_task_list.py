from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.task import TaskResponse
from app.schemas.task_list_item import TaskListItemCreate, TaskListItemResponse, TaskListItemUpdate
from app.services import task_list_service as svc

router = APIRouter(prefix="/api/task-list", tags=["task-list"])


@router.get("/unassigned", response_model=List[TaskListItemResponse])
def list_unassigned(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_unassigned(db)


@router.get("/mine", response_model=List[TaskListItemResponse])
def list_mine(
    status: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_mine(db, user_id, status)


@router.get("/all", response_model=List[TaskListItemResponse])
def list_all(
    assignee_id: Optional[int] = Query(None),
    status: Optional[List[str]] = Query(None),
    q: Optional[str] = Query(None, description="タイトル部分一致フィルタ（大文字小文字を区別しない）"),
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_all(db, assignee_id, status, q, limit=limit, offset=offset)


@router.post("/", response_model=TaskListItemResponse, status_code=201)
def create_item(
    data: TaskListItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_item(db, user_id, data)


@router.get("/{item_id}", response_model=TaskListItemResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_item(db, item_id, user_id)


@router.put("/{item_id}", response_model=TaskListItemResponse)
def update_item(
    item_id: int,
    data: TaskListItemUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_item(db, item_id, user_id, data)


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.delete_item(db, item_id, user_id)
    return Response(status_code=204)


@router.post("/{item_id}/assign", response_model=TaskListItemResponse)
def assign_to_me(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.assign_to_me(db, item_id, user_id)


@router.post("/{item_id}/unassign", response_model=TaskListItemResponse)
def unassign_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.unassign_item(db, item_id, user_id)


@router.post("/{item_id}/start", response_model=TaskResponse)
def start_as_task(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.start_as_task(db, item_id, user_id)
