"""Router registry — add new routers here to auto-register them in main.py."""

from fastapi import APIRouter

from app.routers import (
    api_alert_rules,
    api_alerts,
    api_attendance_presets,
    api_attendances,
    api_auth,
    api_calendar,
    api_groups,
    api_log_sources,
    api_logs,
    api_oauth,
    api_presence,
    api_reports,
    api_summary,
    api_task_categories,
    api_task_list,
    api_tasks,
    api_todos,
    api_users,
    pages,
)

all_routers: list[APIRouter] = [
    pages.router,
    api_todos.router,
    api_attendances.router,
    api_attendance_presets.router,
    api_tasks.router,
    api_logs.router,
    api_users.router,
    api_presence.router,
    api_reports.router,
    api_summary.router,
    api_auth.router,
    api_log_sources.router,
    api_alerts.router,
    api_task_categories.router,
    api_alert_rules.router,
    api_task_list.router,
    api_calendar.router,
    api_groups.router,
    api_oauth.router,
    api_oauth.admin_router,
]
