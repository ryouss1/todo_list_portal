import logging
from typing import List

from sqlalchemy.orm import Session

from app.crud import log as crud_log
from app.models.log import Log
from app.schemas.log import LogCreate
from app.services import alert_service
from app.services.websocket_manager import log_ws_manager

logger = logging.getLogger("app.services.log")


async def create_log(db: Session, data: LogCreate) -> Log:
    logger.info("Log received: system=%s, severity=%s, message=%s", data.system_name, data.severity, data.message[:100])
    log = crud_log.create_log(db, data)

    log_dict = {
        "id": log.id,
        "system_name": log.system_name,
        "log_type": log.log_type,
        "severity": log.severity,
        "message": log.message,
        "extra_data": log.extra_data,
        "received_at": log.received_at.isoformat(),
    }

    await log_ws_manager.broadcast(log_dict)

    # Evaluate alert rules against this log
    await alert_service.evaluate_rules_for_log(db, log_dict)

    return log


def list_logs(db: Session, limit: int = 100) -> List[Log]:
    logger.info("Listing logs: limit=%d", limit)
    return crud_log.get_logs(db, limit)


def list_important_logs(db: Session, limit: int = 100) -> List[Log]:
    logger.info("Listing important logs: limit=%d", limit)
    return crud_log.get_important_logs(db, limit)
