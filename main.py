from app.config import AppConfig
from app.init_db import seed_default_categories, seed_default_presets
from app.routers import pages
from app.routers.api_alert_rules import router as api_alert_rules_router
from app.routers.api_alerts import router as api_alerts_router
from app.routers.api_attendance_presets import router as api_attendance_presets_router
from app.routers.api_attendances import router as api_attendances_router
from app.routers.api_calendar import router as api_calendar_router
from app.routers.api_jobs import router as api_jobs_router
from app.routers.api_log_sources import router as api_log_sources_router
from app.routers.api_logs import router as api_logs_router
from app.routers.api_presence import router as api_presence_router
from app.routers.api_reports import router as api_reports_router
from app.routers.api_sites import group_router as api_sites_group_router
from app.routers.api_sites import router as api_sites_router
from app.routers.api_summary import router as api_summary_router
from app.routers.api_task_categories import router as api_task_categories_router
from app.routers.api_task_list import router as api_task_list_router
from app.routers.api_tasks import router as api_tasks_router
from app.routers.api_todos import router as api_todos_router
from app.routers.api_wiki import category_router as api_wiki_category_router
from app.routers.api_wiki import router as api_wiki_router
from app.routers.api_wiki import tag_router as api_wiki_tag_router
from app.services.alert_service import create_alert_from_scan
from app.services.daily_report_service import create_report_from_task
from app.services.log_scanner import start_scanner, stop_scanner
from app.services.log_source_service import register_on_change_detected
from app.services.reminder_checker import start_reminder_checker, stop_reminder_checker
from app.services.site_checker import start_checker, stop_checker
from app.services.task_service import register_on_task_done
from app.services.websocket_manager import (
    alert_ws_manager,
    calendar_ws_manager,
    log_ws_manager,
    presence_ws_manager,
    site_ws_manager,
)
from portal_core.app_factory import NavItem, PortalApp

# --- Register service hooks ---
register_on_task_done(create_report_from_task)
register_on_change_detected(create_alert_from_scan)

# --- Build application ---
config = AppConfig()
portal = PortalApp(config, title="Todo List Portal")
portal.setup_core()

# === App-specific pages router ===
portal.register_router(pages.router)

# === App-specific API routers ===
portal.register_router(api_todos_router)
portal.register_router(api_attendances_router)
portal.register_router(api_attendance_presets_router)
portal.register_router(api_tasks_router)
portal.register_router(api_logs_router)
portal.register_router(api_presence_router)
portal.register_router(api_reports_router)
portal.register_router(api_summary_router)
portal.register_router(api_log_sources_router)
portal.register_router(api_alerts_router)
portal.register_router(api_task_categories_router)
portal.register_router(api_alert_rules_router)
portal.register_router(api_task_list_router)
portal.register_router(api_calendar_router)
portal.register_router(api_jobs_router)
portal.register_router(api_sites_router)
portal.register_router(api_sites_group_router)
portal.register_router(api_wiki_router)
portal.register_router(api_wiki_category_router)
portal.register_router(api_wiki_tag_router)

# === Authentication-free paths ===
portal.register_public_prefix("/api/logs/")
# Wiki pages with visibility=public are viewable without login.
# Auth middleware lets the request through; visibility check is done at the app layer.
portal.register_public_prefix("/wiki")

# === Navigation items ===
portal.register_nav_item(NavItem("Todo", "/todos", "bi-list-check", sort_order=10, hidden=True))
portal.register_nav_item(NavItem("Public Todos", "/todos/public", "bi-globe", sort_order=11, hidden=True))
portal.register_nav_item(NavItem("Task List", "/task-list", "bi-card-list", sort_order=100))
portal.register_nav_item(NavItem("Attendance", "/attendance", "bi-clock-history", sort_order=200))
portal.register_nav_item(NavItem("Presence", "/presence", "bi-people", sort_order=300))
portal.register_nav_item(NavItem("Tasks", "/tasks", "bi-stopwatch", sort_order=400))
portal.register_nav_item(NavItem("Reports", "/reports", "bi-journal-text", sort_order=500))
portal.register_nav_item(NavItem("Summary", "/summary", "bi-graph-up", sort_order=600))
portal.register_nav_item(NavItem("Calendar", "/calendar", "bi-calendar-event", sort_order=700))
portal.register_nav_item(NavItem("Wiki", "/wiki", "bi-book", sort_order=750))
portal.register_nav_item(NavItem("Sites", "/sites", "bi-link-45deg", sort_order=760))
portal.register_nav_item(NavItem("Logs", "/logs", "bi-terminal", sort_order=800))
portal.register_nav_item(NavItem("Alerts", "/alerts", "bi-bell", badge_id="alert-badge", sort_order=810))

# === WebSocket endpoints ===
portal.register_websocket("/ws/logs", log_ws_manager)
portal.register_websocket("/ws/alerts", alert_ws_manager)
portal.register_websocket("/ws/presence", presence_ws_manager)
portal.register_websocket("/ws/sites", site_ws_manager)
portal.register_websocket("/ws/calendar", calendar_ws_manager)

# === Template and static directories ===
portal.register_template_dir("templates")
portal.register_static_dir("static", "/static")

# === Extra head scripts (loaded after core scripts on every page) ===
portal.register_head_script("/static/js/app_common.js")

# === DB seed hooks ===
portal.register_seed_hook(seed_default_presets)
portal.register_seed_hook(seed_default_categories)

# === Background services ===
portal.register_startup_hook(start_scanner)
portal.register_startup_hook(start_checker)
portal.register_startup_hook(start_reminder_checker)
portal.register_shutdown_hook(stop_scanner)
portal.register_shutdown_hook(stop_checker)
portal.register_shutdown_hook(stop_reminder_checker)

# === Build ===
app = portal.build()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app", "portal_core/portal_core"],
    )
