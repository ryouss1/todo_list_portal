import logging
from typing import List

from sqlalchemy.orm import Session

from app.config import API_PRESENCE_LOG_LIMIT, PRESENCE_ACTIVE_TASK_LIMIT
from app.constants import PresenceStatusValue
from app.crud import presence as crud_presence
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.models.presence import PresenceStatus
from app.schemas.presence import ActiveTicket, PresenceStatusWithUser

logger = logging.getLogger("app.services.presence")


def update_status(db: Session, user_id: int, status: str, message: str = None) -> PresenceStatus:
    logger.info("Updating presence: user_id=%d, status=%s", user_id, status)
    result = crud_presence.upsert_presence_status(db, user_id, status, message)
    crud_presence.create_presence_log(db, user_id, status, message)
    return result


def get_my_status(db: Session, user_id: int) -> PresenceStatus:
    existing = crud_presence.get_presence_status(db, user_id)
    if existing:
        return existing
    return PresenceStatus(id=0, user_id=user_id, status=PresenceStatusValue.OFFLINE, message=None, updated_at=None)


def get_all_statuses(db: Session, limit: int = 500, offset: int = 0) -> List[PresenceStatusWithUser]:
    statuses = crud_presence.get_all_presence_statuses(db)
    users = crud_user.get_users(db, active_only=True)

    active_tasks = crud_task.get_in_progress_with_backlog(db, limit=PRESENCE_ACTIVE_TASK_LIMIT)
    tickets_by_user = {}
    for task in active_tasks:
        tickets_by_user.setdefault(task.user_id, []).append(
            ActiveTicket(
                task_id=task.id,
                task_title=task.title,
                backlog_ticket_id=task.backlog_ticket_id,
            )
        )

    active_user_ids = {u.id for u in users}
    status_map = {s.user_id: s for s in statuses if s.user_id in active_user_ids}
    result = []
    for user in users:
        s = status_map.get(user.id)
        result.append(
            PresenceStatusWithUser(
                user_id=user.id,
                display_name=user.display_name,
                status=s.status if s else PresenceStatusValue.OFFLINE,
                message=s.message if s else None,
                updated_at=s.updated_at if s else None,
                active_tickets=tickets_by_user.get(user.id, []),
            )
        )
    return result[offset : offset + limit]


def get_logs(db: Session, user_id: int):
    return crud_presence.get_presence_logs(db, user_id, API_PRESENCE_LOG_LIMIT)
