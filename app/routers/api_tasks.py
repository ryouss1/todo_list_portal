from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.daily_report import DailyReportResponse
from app.schemas.task import (
    BatchDoneRequest,
    BatchDoneResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TimeEntryResponse,
)
from app.services import task_service as svc_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.list_tasks(db, user_id)


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.create_task(db, user_id, data)


@router.post("/batch-done", response_model=BatchDoneResponse)
def batch_done(data: BatchDoneRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    results = svc_task.batch_done(db, user_id, data.tasks)
    return BatchDoneResponse(results=results)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.get_task(db, task_id, user_id)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int, data: TaskUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    return svc_task.update_task(db, task_id, user_id, data)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    svc_task.delete_task(db, task_id, user_id)


@router.post("/{task_id}/done")
def done_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    report = svc_task.done_task(db, task_id, user_id)
    if report:
        return JSONResponse(status_code=200, content=DailyReportResponse.model_validate(report).model_dump(mode="json"))
    return Response(status_code=204)


@router.post("/{task_id}/start", response_model=TimeEntryResponse)
def start_timer(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.start_timer(db, task_id, user_id)


@router.post("/{task_id}/stop", response_model=TimeEntryResponse)
def stop_timer(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.stop_timer(db, task_id, user_id)


@router.get("/{task_id}/time-entries", response_model=List[TimeEntryResponse])
def get_time_entries(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_task.get_time_entries(db, task_id, user_id)
