from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import BOOTSTRAP_CSS_URL, BOOTSTRAP_ICONS_URL, FULLCALENDAR_JS_URL
from app.core.i18n import get_translator

router = APIRouter(tags=["pages"])

# Jinja2 environment with i18n extension
_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"]),
    extensions=["jinja2.ext.i18n"],
)
# Install default translations
_env.install_gettext_translations(get_translator())


def _render(template_name: str, request: Request, **context) -> HTMLResponse:
    """Render a template with locale-aware translations."""
    locale = getattr(request.state, "locale", "ja")
    _env.install_gettext_translations(get_translator(locale))
    template = _env.get_template(template_name)
    html = template.render(request=request, **context)
    return HTMLResponse(html)


@router.get("/login")
def login_page(request: Request):
    return _render(
        "login.html",
        request,
        bootstrap_css_url=BOOTSTRAP_CSS_URL,
        bootstrap_icons_url=BOOTSTRAP_ICONS_URL,
    )


@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return _render(
        "forgot_password.html",
        request,
        bootstrap_css_url=BOOTSTRAP_CSS_URL,
        bootstrap_icons_url=BOOTSTRAP_ICONS_URL,
    )


@router.get("/reset-password")
def reset_password_page(request: Request):
    return _render(
        "reset_password.html",
        request,
        bootstrap_css_url=BOOTSTRAP_CSS_URL,
        bootstrap_icons_url=BOOTSTRAP_ICONS_URL,
    )


@router.get("/")
def index(request: Request):
    return _render("index.html", request)


@router.get("/todos")
def todos_page(request: Request):
    return _render("todos.html", request)


@router.get("/todos/public")
def todos_public_page(request: Request):
    return _render("todos_public.html", request)


@router.get("/presence")
def presence_page(request: Request):
    return _render("presence.html", request)


@router.get("/attendance")
def attendance_page(request: Request):
    return _render("attendance.html", request)


@router.get("/summary")
def summary_page(request: Request):
    return _render("summary.html", request)


@router.get("/reports")
def reports_page(request: Request):
    return _render("reports.html", request)


@router.get("/reports/{report_id}")
def report_detail_page(request: Request, report_id: int):
    return _render("report_detail.html", request, report_id=report_id)


@router.get("/tasks")
def tasks_page(request: Request):
    return _render("tasks.html", request)


@router.get("/task-list")
def task_list_page(request: Request):
    return _render("task_list.html", request)


@router.get("/logs")
def logs_page(request: Request):
    return _render("logs.html", request)


@router.get("/alerts")
def alerts_page(request: Request):
    return _render("alerts.html", request)


@router.get("/calendar")
def calendar_page(request: Request):
    return _render(
        "calendar.html",
        request,
        fullcalendar_js_url=FULLCALENDAR_JS_URL,
    )


@router.get("/users")
def users_page(request: Request):
    return _render("users.html", request)
