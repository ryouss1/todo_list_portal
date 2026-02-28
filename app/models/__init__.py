# ============================================================
# Core models (portal_core) — will move to portal_core/models/ in Phase 2
# ============================================================
# ============================================================
# App-specific models — remain in app/models/
# ============================================================
from app.models.alert import Alert, AlertRule
from app.models.attendance import Attendance
from app.models.attendance_break import AttendanceBreak
from app.models.attendance_preset import AttendancePreset
from app.models.auth_audit_log import AuthAuditLog
from app.models.calendar_event import CalendarEvent, CalendarEventException
from app.models.calendar_event_attendee import CalendarEventAttendee
from app.models.calendar_reminder import CalendarReminder
from app.models.calendar_room import CalendarRoom
from app.models.daily_report import DailyReport
from app.models.log import Log
from app.models.log_entry import LogEntry
from app.models.log_file import LogFile
from app.models.log_source import LogSource
from app.models.log_source_path import LogSourcePath
from app.models.login_attempt import LoginAttempt
from app.models.oauth_provider import OAuthProvider
from app.models.oauth_state import OAuthState
from app.models.password_reset_token import PasswordResetToken
from app.models.presence import PresenceLog, PresenceStatus
from app.models.site_link import SiteGroup, SiteLink
from app.models.task import Task
from app.models.task_category import TaskCategory
from app.models.task_list_item import TaskListItem
from app.models.task_time_entry import TaskTimeEntry
from app.models.todo import Todo
from app.models.user import User
from app.models.user_calendar_setting import UserCalendarSetting
from app.models.user_oauth_account import UserOAuthAccount
from app.models.wiki_attachment import WikiAttachment
from app.models.wiki_category import WikiCategory
from app.models.wiki_page import WikiPage
from app.models.wiki_tag import WikiTag, wiki_page_tags
from app.models.wiki_task_link import WikiPageTask, wiki_page_task_items
from portal_core.models.department import Department

__all__ = [
    # Core models
    "User",
    "Department",
    "LoginAttempt",
    "AuthAuditLog",
    "OAuthProvider",
    "UserOAuthAccount",
    "OAuthState",
    "PasswordResetToken",
    # App-specific models
    "Todo",
    "Attendance",
    "AttendanceBreak",
    "AttendancePreset",
    "Task",
    "TaskCategory",
    "TaskTimeEntry",
    "Log",
    "LogEntry",
    "LogFile",
    "LogSource",
    "LogSourcePath",
    "Alert",
    "AlertRule",
    "PresenceStatus",
    "PresenceLog",
    "DailyReport",
    "TaskListItem",
    "CalendarEvent",
    "CalendarEventException",
    "CalendarEventAttendee",
    "CalendarReminder",
    "CalendarRoom",
    "UserCalendarSetting",
    "SiteGroup",
    "SiteLink",
    # Wiki models
    "WikiAttachment",
    "WikiCategory",
    "WikiTag",
    "WikiPage",
    "WikiPageTask",
    "wiki_page_tags",
    "wiki_page_task_items",
]
