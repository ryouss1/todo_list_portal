import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from dateutil.rrule import rrulestr
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.crud import calendar_attendee as crud_att
from app.crud import calendar_event as crud_event
from app.crud import calendar_reminder as crud_reminder
from app.crud import calendar_room as crud_room
from app.models.calendar_event import CalendarEvent
from app.models.calendar_room import CalendarRoom
from app.models.user import User
from app.models.user_calendar_setting import UserCalendarSetting
from app.schemas.calendar import (
    AttendeeInfo,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarRoomResponse,
    CalendarRoomUpdate,
    FullCalendarEvent,
    RoomAvailability,
    RoomReservation,
    UserCalendarSettingResponse,
    UserCalendarSettingUpdate,
)

logger = logging.getLogger("app.services.calendar")

# Color palette for multi-user display
USER_COLORS = [
    "#3788d8",
    "#e74c3c",
    "#2ecc71",
    "#f39c12",
    "#9b59b6",
    "#1abc9c",
    "#e67e22",
    "#3498db",
    "#e91e63",
    "#00bcd4",
    "#ff9800",
    "#8bc34a",
]

SOURCE_COLORS = {
    "task_list": "#6c757d",
    "attendance": "#adb5bd",
    "report": "#198754",
}


# --- Event CRUD ---


def get_event(db: Session, event_id: int, user_id: int) -> CalendarEventResponse:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    return _to_response(db, event, user_id)


def list_events_fullcalendar(
    db: Session,
    user_id: int,
    start: datetime,
    end: datetime,
    user_ids: Optional[List[int]] = None,
    include_source: bool = True,
) -> List[FullCalendarEvent]:
    """Get events formatted for FullCalendar."""
    # Regular (non-recurring) events
    non_recurring = crud_event.get_events_in_range(db, start, end, user_ids)
    non_recurring = [e for e in non_recurring if e.recurrence_rule is None]

    # Recurring events expanded
    recurring = crud_event.get_recurring_events_in_range(db, start, end, user_ids)

    user_map = _get_user_map(db)
    color_map = _get_user_color_map(db, user_map)

    result = []

    # Add non-recurring events
    for event in non_recurring:
        fc = _event_to_fullcalendar(event, user_id, user_map, color_map)
        if fc:
            result.append(fc)

    # Expand recurring events
    for event in recurring:
        occurrences = _expand_recurrence(db, event, start, end)
        for occ_start, occ_end in occurrences:
            fc = _event_to_fullcalendar(event, user_id, user_map, color_map, occ_start, occ_end)
            if fc:
                # Use composite ID for occurrences
                fc.id = f"{event.id}_{occ_start.strftime('%Y%m%d')}"
                result.append(fc)

    # Source events (TaskListItem, Attendance, DailyReport)
    if include_source:
        settings = _get_settings(db, user_id)
        source_events = _get_source_events(db, start, end, user_ids, settings, user_map)
        result.extend(source_events)

    return result


def create_event(db: Session, user_id: int, data: CalendarEventCreate) -> CalendarEventResponse:
    # Room conflict check
    if data.room_id and data.end_at:
        _check_room_conflict(db, data.room_id, data.start_at, data.end_at)
    # Auto-fill location from room
    if data.room_id:
        room = crud_room.get_room(db, data.room_id)
        if room:
            data.location = room.name

    event = crud_event.create_event(db, user_id, data)
    logger.info("Calendar event created: id=%d, title=%s", event.id, event.title)

    # Add attendees
    if data.attendee_ids:
        for uid in data.attendee_ids:
            if uid != user_id:
                crud_att.add_attendee(db, event.id, uid)
        # Creator is always an accepted attendee
    crud_att.add_attendee(db, event.id, user_id)
    att = crud_att.get_attendee(db, event.id, user_id)
    if att:
        crud_att.update_response(db, att, "accepted")

    # Set reminder
    if data.reminder_minutes is not None:
        remind_at = event.start_at - timedelta(minutes=data.reminder_minutes)
        crud_reminder.set_reminder(db, event.id, user_id, data.reminder_minutes, remind_at)

    return _to_response(db, event, user_id)


def update_event(
    db: Session,
    event_id: int,
    user_id: int,
    data: CalendarEventUpdate,
    scope: str = "all",
) -> CalendarEventResponse:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if event.creator_id != user_id:
        raise ForbiddenError("Only creator can update event")

    # Room conflict check on update
    update_data = data.model_dump(exclude_unset=True)
    new_room_id = update_data.get("room_id", event.room_id)
    new_start = update_data.get("start_at", event.start_at)
    new_end = update_data.get("end_at", event.end_at)
    if new_room_id and new_end:
        _check_room_conflict(db, new_room_id, new_start, new_end, exclude_event_id=event_id)
    # Auto-fill location from room
    if "room_id" in update_data and new_room_id:
        room = crud_room.get_room(db, new_room_id)
        if room:
            data.location = room.name

    if scope == "this" and event.recurrence_rule:
        # Create exception + override event for this occurrence
        original_date = data.start_at.date() if data.start_at else event.start_at.date()
        override = crud_event.create_event(
            db,
            user_id,
            CalendarEventCreate(
                title=data.title or event.title,
                description=data.description if data.description is not None else event.description,
                event_type=data.event_type or event.event_type,
                start_at=data.start_at or event.start_at,
                end_at=data.end_at if data.end_at is not None else event.end_at,
                all_day=data.all_day if data.all_day is not None else event.all_day,
                location=data.location if data.location is not None else event.location,
                color=data.color if data.color is not None else event.color,
                visibility=data.visibility or event.visibility,
            ),
        )
        crud_event.create_exception(db, event.id, original_date, override_event_id=override.id)
        return _to_response(db, override, user_id)

    updated = crud_event.update_event(db, event, data)

    # Update reminders if start_at changed
    if data.start_at is not None:
        _update_reminders_for_event(db, event_id, updated.start_at)

    logger.info("Calendar event updated: id=%d", event_id)
    return _to_response(db, updated, user_id)


def delete_event(db: Session, event_id: int, user_id: int, scope: str = "all") -> None:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if event.creator_id != user_id:
        raise ForbiddenError("Only creator can delete event")

    if scope == "this" and event.recurrence_rule:
        # Mark this occurrence as deleted
        crud_event.create_exception(db, event.id, date.today(), is_deleted=True)
    else:
        crud_event.delete_event(db, event)

    logger.info("Calendar event deleted: id=%d, scope=%s", event_id, scope)


# --- Attendees ---


def add_attendees(db: Session, event_id: int, user_id: int, user_ids: List[int]) -> List[AttendeeInfo]:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if event.creator_id != user_id:
        raise ForbiddenError("Only creator can add attendees")

    user_map = _get_user_map(db)
    for uid in user_ids:
        existing = crud_att.get_attendee(db, event_id, uid)
        if not existing:
            crud_att.add_attendee(db, event_id, uid)

    return _get_attendee_list(db, event_id, user_map)


def remove_attendee(db: Session, event_id: int, user_id: int, target_user_id: int) -> None:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if event.creator_id != user_id:
        raise ForbiddenError("Only creator can remove attendees")

    att = crud_att.get_attendee(db, event_id, target_user_id)
    if not att:
        raise NotFoundError("Attendee not found")
    crud_att.remove_attendee(db, att)


def respond_to_event(db: Session, event_id: int, user_id: int, status: str) -> AttendeeInfo:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")

    att = crud_att.get_attendee(db, event_id, user_id)
    if not att:
        raise NotFoundError("You are not an attendee of this event")

    updated = crud_att.update_response(db, att, status)
    user_map = _get_user_map(db)
    return AttendeeInfo(
        user_id=updated.user_id,
        display_name=user_map.get(updated.user_id, ""),
        response_status=updated.response_status,
    )


# --- Reminders ---


def set_reminder(db: Session, event_id: int, user_id: int, minutes_before: int) -> None:
    event = crud_event.get_event(db, event_id)
    if not event:
        raise NotFoundError("Event not found")
    remind_at = event.start_at - timedelta(minutes=minutes_before)
    crud_reminder.set_reminder(db, event_id, user_id, minutes_before, remind_at)


def delete_reminder(db: Session, event_id: int, user_id: int) -> None:
    reminder = crud_reminder.get_reminder(db, event_id, user_id)
    if not reminder:
        raise NotFoundError("Reminder not found")
    crud_reminder.delete_reminder(db, reminder)


# --- Rooms ---


def get_active_rooms(db: Session) -> List[CalendarRoomResponse]:
    rooms = crud_room.get_active_rooms(db)
    return [CalendarRoomResponse.model_validate(r) for r in rooms]


def get_all_rooms(db: Session) -> List[CalendarRoomResponse]:
    rooms = crud_room.get_all_rooms(db)
    return [CalendarRoomResponse.model_validate(r) for r in rooms]


def create_room(
    db: Session,
    name: str,
    description: Optional[str] = None,
    capacity: Optional[int] = None,
    color: Optional[str] = None,
    sort_order: int = 0,
) -> CalendarRoomResponse:
    # Check unique name
    existing = db.query(CalendarRoom).filter(CalendarRoom.name == name).first()
    if existing:
        raise ConflictError(f"Room with name '{name}' already exists")
    room = crud_room.create_room(db, name, description, capacity, color, sort_order)
    return CalendarRoomResponse.model_validate(room)


def update_room(db: Session, room_id: int, data: CalendarRoomUpdate) -> CalendarRoomResponse:
    room = crud_room.get_room(db, room_id)
    if not room:
        raise NotFoundError("Room not found")
    update_data = data.model_dump(exclude_unset=True)
    # Check unique name if being changed
    if "name" in update_data and update_data["name"] != room.name:
        existing = db.query(CalendarRoom).filter(CalendarRoom.name == update_data["name"]).first()
        if existing:
            raise ConflictError(f"Room with name '{update_data['name']}' already exists")
    updated = crud_room.update_room(db, room, update_data)
    return CalendarRoomResponse.model_validate(updated)


def delete_room(db: Session, room_id: int) -> None:
    room = crud_room.get_room(db, room_id)
    if not room:
        raise NotFoundError("Room not found")
    # Logical delete
    room.is_active = False
    db.commit()


def get_room_availability(db: Session, room_id: int, target_date: date) -> RoomAvailability:
    room = crud_room.get_room(db, room_id)
    if not room:
        raise NotFoundError("Room not found")
    date_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    date_end = date_start + timedelta(days=1)
    events = crud_room.get_room_reservations(db, room_id, date_start, date_end)
    user_map = _get_user_map(db)
    reservations = [
        RoomReservation(
            event_id=e.id,
            title=e.title,
            start=e.start_at.strftime("%H:%M"),
            end=e.end_at.strftime("%H:%M") if e.end_at else "",
            creator_name=user_map.get(e.creator_id, ""),
        )
        for e in events
    ]
    return RoomAvailability(
        room_id=room.id,
        room_name=room.name,
        date=target_date.isoformat(),
        reservations=reservations,
    )


# --- Settings ---


def get_settings(db: Session, user_id: int) -> UserCalendarSettingResponse:
    settings = _get_settings(db, user_id)
    return UserCalendarSettingResponse.model_validate(settings)


def update_settings(db: Session, user_id: int, data: UserCalendarSettingUpdate) -> UserCalendarSettingResponse:
    settings = _get_settings(db, user_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return UserCalendarSettingResponse.model_validate(settings)


# --- Internal helpers ---


def _get_settings(db: Session, user_id: int) -> UserCalendarSetting:
    settings = db.query(UserCalendarSetting).filter(UserCalendarSetting.user_id == user_id).first()
    if not settings:
        settings = UserCalendarSetting(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _check_room_conflict(
    db: Session, room_id: int, start_at: datetime, end_at: datetime, exclude_event_id: Optional[int] = None
) -> None:
    """Raise ConflictError if room has a conflicting reservation."""
    conflict = crud_room.check_room_conflict(db, room_id, start_at, end_at, exclude_event_id)
    if conflict:
        room = crud_room.get_room(db, room_id)
        room_name = room.name if room else str(room_id)
        raise ConflictError(f"この時間帯は「{room_name}」が既に予約されています")


def _get_room_map(db: Session) -> dict:
    rooms = crud_room.get_active_rooms(db)
    return {r.id: r.name for r in rooms}


def _get_user_map(db: Session) -> dict:
    users = db.query(User).all()
    return {u.id: u.display_name or u.email for u in users}


def _get_user_color_map(db: Session, user_map: dict) -> dict:
    """Build user_id -> color mapping from settings or default palette."""
    color_map = {}
    settings_list = db.query(UserCalendarSetting).all()
    settings_by_user = {s.user_id: s.default_color for s in settings_list}

    for i, uid in enumerate(sorted(user_map.keys())):
        if uid in settings_by_user:
            color_map[uid] = settings_by_user[uid]
        else:
            color_map[uid] = USER_COLORS[i % len(USER_COLORS)]
    return color_map


def _to_response(db: Session, event: CalendarEvent, requesting_user_id: int) -> CalendarEventResponse:
    user_map = _get_user_map(db)
    room_map = _get_room_map(db)
    attendees = _get_attendee_list(db, event.id, user_map)

    # For private events, mask details for non-creators
    if event.visibility == "private" and event.creator_id != requesting_user_id:
        return CalendarEventResponse(
            id=event.id,
            title="予定あり",
            event_type=event.event_type,
            start_at=event.start_at,
            end_at=event.end_at,
            all_day=event.all_day,
            visibility="private",
            creator_id=event.creator_id,
            creator_name=user_map.get(event.creator_id, ""),
            attendees=[],
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    # Get reminder for requesting user
    reminder = crud_reminder.get_reminder(db, event.id, requesting_user_id)

    return CalendarEventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        start_at=event.start_at,
        end_at=event.end_at,
        all_day=event.all_day,
        room_id=event.room_id,
        room_name=room_map.get(event.room_id) if event.room_id else None,
        location=event.location,
        color=event.color,
        visibility=event.visibility,
        recurrence_rule=event.recurrence_rule,
        recurrence_end=event.recurrence_end,
        source_type=event.source_type,
        source_id=event.source_id,
        creator_id=event.creator_id,
        creator_name=user_map.get(event.creator_id, ""),
        attendees=attendees,
        my_reminder_minutes=reminder.minutes_before if reminder else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _get_attendee_list(db: Session, event_id: int, user_map: dict) -> List[AttendeeInfo]:
    attendees = crud_att.get_attendees(db, event_id)
    return [
        AttendeeInfo(
            user_id=a.user_id,
            display_name=user_map.get(a.user_id, ""),
            response_status=a.response_status,
        )
        for a in attendees
    ]


def _event_to_fullcalendar(
    event: CalendarEvent,
    requesting_user_id: int,
    user_map: dict,
    color_map: dict,
    override_start: Optional[datetime] = None,
    override_end: Optional[datetime] = None,
) -> Optional[FullCalendarEvent]:
    start = override_start or event.start_at
    end = override_end or event.end_at
    color = event.color or color_map.get(event.creator_id, "#3788d8")

    if event.visibility == "private" and event.creator_id != requesting_user_id:
        return FullCalendarEvent(
            id=str(event.id),
            title="予定あり",
            start=start.isoformat(),
            end=end.isoformat() if end else None,
            allDay=event.all_day,
            color="#dee2e6",
            textColor="#666666",
            extendedProps={
                "event_type": event.event_type,
                "visibility": "private",
                "creator_id": event.creator_id,
                "creator_name": user_map.get(event.creator_id, ""),
            },
        )

    return FullCalendarEvent(
        id=str(event.id),
        title=event.title,
        start=start.isoformat(),
        end=end.isoformat() if end else None,
        allDay=event.all_day,
        color=color,
        extendedProps={
            "event_type": event.event_type,
            "description": event.description,
            "location": event.location,
            "room_id": event.room_id,
            "visibility": event.visibility,
            "creator_id": event.creator_id,
            "creator_name": user_map.get(event.creator_id, ""),
            "recurrence_rule": event.recurrence_rule,
            "source_type": event.source_type,
            "source_id": event.source_id,
        },
    )


def _expand_recurrence(
    db: Session,
    event: CalendarEvent,
    range_start: datetime,
    range_end: datetime,
) -> List[tuple]:
    """Expand RRULE into (start, end) tuples within range."""
    if not event.recurrence_rule:
        return []

    try:
        rule = rrulestr(event.recurrence_rule, dtstart=event.start_at.replace(tzinfo=None))
    except (ValueError, TypeError):
        logger.warning("Invalid RRULE for event %d: %s", event.id, event.recurrence_rule)
        return []

    # Get exceptions for this event
    exceptions = crud_event.get_exceptions(db, event.id)
    deleted_dates = {exc.original_date for exc in exceptions if exc.is_deleted}

    duration = (event.end_at - event.start_at) if event.end_at else timedelta(hours=1)

    naive_start = range_start.replace(tzinfo=None)
    naive_end = range_end.replace(tzinfo=None)

    occurrences = []
    for dt in rule.between(naive_start, naive_end, inc=True):
        if dt.date() in deleted_dates:
            continue
        occ_start = dt.replace(tzinfo=timezone.utc)
        occ_end = occ_start + duration
        occurrences.append((occ_start, occ_end))

        # Safety limit
        if len(occurrences) >= 365:
            break

    return occurrences


def _get_source_events(
    db: Session,
    start: datetime,
    end: datetime,
    user_ids: Optional[List[int]],
    settings: UserCalendarSetting,
    user_map: dict,
) -> List[FullCalendarEvent]:
    """Generate FullCalendar events from TaskListItem, Attendance, DailyReport."""
    result = []
    start_date = start.date() if hasattr(start, "date") else start
    end_date = end.date() if hasattr(end, "date") else end

    if settings.show_task_list:
        from app.models.task_list_item import TaskListItem

        query = db.query(TaskListItem).filter(
            TaskListItem.scheduled_date.isnot(None),
            TaskListItem.scheduled_date >= start_date,
            TaskListItem.scheduled_date < end_date,
        )
        if user_ids:
            query = query.filter(TaskListItem.assignee_id.in_(user_ids))
        for item in query.all():
            assignee_name = user_map.get(item.assignee_id, "") if item.assignee_id else ""
            result.append(
                FullCalendarEvent(
                    id=f"tli_{item.id}",
                    title=f"[Task] {item.title}",
                    start=item.scheduled_date.isoformat(),
                    allDay=True,
                    color=SOURCE_COLORS["task_list"],
                    extendedProps={
                        "source_type": "task_list",
                        "source_id": item.id,
                        "creator_name": assignee_name,
                        "status": item.status,
                        "read_only": True,
                    },
                )
            )

    if settings.show_attendance:
        from app.models.attendance import Attendance

        query = db.query(Attendance).filter(
            Attendance.date >= start_date,
            Attendance.date < end_date,
        )
        if user_ids:
            query = query.filter(Attendance.user_id.in_(user_ids))
        for att in query.all():
            user_name = user_map.get(att.user_id, "")
            result.append(
                FullCalendarEvent(
                    id=f"att_{att.id}",
                    title=f"[出勤] {user_name}",
                    start=att.clock_in.isoformat() if att.clock_in else att.date.isoformat(),
                    end=att.clock_out.isoformat() if att.clock_out else None,
                    allDay=not att.clock_in,
                    color=SOURCE_COLORS["attendance"],
                    extendedProps={
                        "source_type": "attendance",
                        "source_id": att.id,
                        "creator_name": user_name,
                        "read_only": True,
                    },
                )
            )

    if settings.show_reports:
        from app.models.daily_report import DailyReport

        query = db.query(DailyReport).filter(
            DailyReport.report_date >= start_date,
            DailyReport.report_date < end_date,
        )
        if user_ids:
            query = query.filter(DailyReport.user_id.in_(user_ids))
        for rpt in query.all():
            user_name = user_map.get(rpt.user_id, "")
            result.append(
                FullCalendarEvent(
                    id=f"rpt_{rpt.id}",
                    title=f"[日報] {rpt.task_name or user_name}",
                    start=rpt.report_date.isoformat(),
                    allDay=True,
                    color=SOURCE_COLORS["report"],
                    extendedProps={
                        "source_type": "report",
                        "source_id": rpt.id,
                        "creator_name": user_name,
                        "read_only": True,
                    },
                )
            )

    return result


def _update_reminders_for_event(db: Session, event_id: int, new_start: datetime) -> None:
    """Update remind_at for all reminders of an event when start_at changes."""
    from app.models.calendar_reminder import CalendarReminder

    reminders = db.query(CalendarReminder).filter(CalendarReminder.event_id == event_id).all()
    for r in reminders:
        r.remind_at = new_start - timedelta(minutes=r.minutes_before)
        r.is_sent = False
    db.commit()
