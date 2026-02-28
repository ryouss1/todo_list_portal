"""Background job status API (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import require_admin
from app.services import log_scanner, reminder_checker, site_checker

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_SERVICES = {
    "log_scanner": log_scanner,
    "site_checker": site_checker,
    "reminder_checker": reminder_checker,
}


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


@router.post("/{name}/restart", dependencies=[Depends(require_admin)])
async def restart_job(name: str, request: Request):
    """Restart a named background job. Admin only."""
    svc = _SERVICES.get(name)
    if svc is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {name}")
    return await svc.restart(request.app)
