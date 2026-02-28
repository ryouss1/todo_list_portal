"""App-specific page routes.

Core pages (login, forgot-password, reset-password, users, dashboard) are
handled by PortalApp in portal_core.  This module only contains routes for
app-specific pages.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config import FULLCALENDAR_JS_URL

router = APIRouter(tags=["pages"])


def _render(request: Request, template_name: str, **context) -> HTMLResponse:
    """Delegate rendering to PortalApp's render function stored on app.state."""
    return request.app.state.render(template_name, request, **context)


@router.get("/todos")
def todos_page(request: Request):
    return _render(request, "todos.html")


@router.get("/todos/public")
def todos_public_page(request: Request):
    return _render(request, "todos_public.html")


@router.get("/presence")
def presence_page(request: Request):
    return _render(request, "presence.html")


@router.get("/attendance")
def attendance_page(request: Request):
    return _render(request, "attendance.html")


@router.get("/summary")
def summary_page(request: Request):
    return _render(request, "summary.html")


@router.get("/reports")
def reports_page(request: Request):
    return _render(request, "reports.html")


@router.get("/reports/{report_id}")
def report_detail_page(request: Request, report_id: int):
    return _render(request, "report_detail.html", report_id=report_id)


@router.get("/tasks")
def tasks_page(request: Request):
    return _render(request, "tasks.html")


@router.get("/task-list")
def task_list_page(request: Request):
    return _render(request, "task_list.html")


@router.get("/sites")
def sites_page(request: Request):
    return _render(request, "sites.html")


@router.get("/logs")
def logs_page(request: Request):
    return _render(request, "logs.html")


@router.get("/alerts")
def alerts_page(request: Request):
    return _render(request, "alerts.html")


@router.get("/calendar")
def calendar_page(request: Request):
    return _render(
        request,
        "calendar.html",
        fullcalendar_js_url=FULLCALENDAR_JS_URL,
    )


@router.get("/wiki")
def wiki_list_page(request: Request):
    return _render(request, "wiki.html")


@router.get("/wiki/new")
def wiki_new_page(request: Request):
    return _render(request, "wiki_edit.html", page_id=None, slug=None)


@router.get("/wiki/{slug}/edit")
def wiki_edit_page(request: Request, slug: str):
    return _render(request, "wiki_edit.html", slug=slug)


@router.get("/wiki/{slug}")
def wiki_page(request: Request, slug: str):
    return _render(request, "wiki_page.html", slug=slug)
