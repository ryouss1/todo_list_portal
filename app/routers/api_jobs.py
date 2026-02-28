"""Background job status API (admin only)."""

from fastapi import APIRouter, Depends, Request

from app.core.deps import require_admin
from app.services import log_scanner, reminder_checker, site_checker

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/status", dependencies=[Depends(require_admin)])
def get_jobs_status(request: Request):
    """Return health status of all background jobs. Admin only."""
    return {
        "jobs": [
            log_scanner.get_status(request.app),
            site_checker.get_status(request.app),
            reminder_checker.get_status(request.app),
        ]
    }
