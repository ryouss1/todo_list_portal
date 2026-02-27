"""Router registry — app-specific routers only.

Core routers (auth, users, departments, OAuth) are now registered by PortalApp
in portal_core.  This module only exports app-specific routers for backward
compatibility with code that imports from ``app.routers``.
"""

from app.routers import (
    api_alert_rules,
    api_alerts,
    api_attendance_presets,
    api_attendances,
    api_calendar,
    api_groups,
    api_log_sources,
    api_logs,
    api_presence,
    api_reports,
    api_sites,
    api_summary,
    api_task_categories,
    api_task_list,
    api_tasks,
    api_todos,
    pages,
)

# App-specific routers (core routers are registered by PortalApp)
_app_routers = [
    pages.router,
    api_todos.router,
    api_attendances.router,
    api_attendance_presets.router,
    api_tasks.router,
    api_logs.router,
    api_presence.router,
    api_reports.router,
    api_summary.router,
    api_log_sources.router,
    api_alerts.router,
    api_task_categories.router,
    api_alert_rules.router,
    api_groups.router,
    api_task_list.router,
    api_calendar.router,
    api_sites.router,
    api_sites.group_router,
]

# Backward compatibility — code that does `from app.routers import all_routers`
all_routers = _app_routers
