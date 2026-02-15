from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import BOOTSTRAP_CSS_URL, BOOTSTRAP_ICONS_URL, FULLCALENDAR_JS_URL

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "bootstrap_css_url": BOOTSTRAP_CSS_URL,
            "bootstrap_icons_url": BOOTSTRAP_ICONS_URL,
        },
    )


@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "bootstrap_css_url": BOOTSTRAP_CSS_URL,
            "bootstrap_icons_url": BOOTSTRAP_ICONS_URL,
        },
    )


@router.get("/reset-password")
def reset_password_page(request: Request):
    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "bootstrap_css_url": BOOTSTRAP_CSS_URL,
            "bootstrap_icons_url": BOOTSTRAP_ICONS_URL,
        },
    )


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/todos")
def todos_page(request: Request):
    return templates.TemplateResponse("todos.html", {"request": request})


@router.get("/todos/public")
def todos_public_page(request: Request):
    return templates.TemplateResponse("todos_public.html", {"request": request})


@router.get("/presence")
def presence_page(request: Request):
    return templates.TemplateResponse("presence.html", {"request": request})


@router.get("/attendance")
def attendance_page(request: Request):
    return templates.TemplateResponse("attendance.html", {"request": request})


@router.get("/summary")
def summary_page(request: Request):
    return templates.TemplateResponse("summary.html", {"request": request})


@router.get("/reports")
def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})


@router.get("/reports/{report_id}")
def report_detail_page(request: Request, report_id: int):
    return templates.TemplateResponse("report_detail.html", {"request": request, "report_id": report_id})


@router.get("/tasks")
def tasks_page(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})


@router.get("/task-list")
def task_list_page(request: Request):
    return templates.TemplateResponse("task_list.html", {"request": request})


@router.get("/logs")
def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


@router.get("/alerts")
def alerts_page(request: Request):
    return templates.TemplateResponse("alerts.html", {"request": request})


@router.get("/calendar")
def calendar_page(request: Request):
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "fullcalendar_js_url": FULLCALENDAR_JS_URL,
        },
    )


@router.get("/users")
def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})
