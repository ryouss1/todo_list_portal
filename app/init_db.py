"""App-specific seed functions for Todo List Portal.

Core seed (seed_default_user) is in app/core/init_db.py.
"""

import logging

# Re-export for backward compatibility (main.py imports from here)
from app.core.init_db import seed_default_user  # noqa: F401
from app.database import SessionLocal
from app.models.attendance_preset import AttendancePreset
from app.models.calendar_room import CalendarRoom
from app.models.task_category import TaskCategory

logger = logging.getLogger("app.init_db")


def seed_default_presets():
    db = SessionLocal()
    try:
        existing = db.query(AttendancePreset).count()
        if existing == 0:
            presets = [
                AttendancePreset(
                    id=1, name="9:00-18:00", clock_in="09:00", clock_out="18:00", break_start="12:00", break_end="13:00"
                ),
                AttendancePreset(
                    id=2, name="8:30-17:30", clock_in="08:30", clock_out="17:30", break_start="12:00", break_end="13:00"
                ),
            ]
            db.add_all(presets)
            db.commit()
            logger.info("Default attendance presets seeded (2 presets).")
        else:
            logger.info("Attendance presets already exist (%d).", existing)
    finally:
        db.close()


DEFAULT_ROOMS = [
    (1, "大会議室", "3F 最大20名", 20, 1),
    (2, "中会議室", "3F 最大10名", 10, 2),
    (3, "小会議室", "3F 最大4名", 4, 3),
]


def seed_default_rooms():
    db = SessionLocal()
    try:
        from sqlalchemy import text

        existing_ids = {row.id for row in db.query(CalendarRoom.id).all()}
        new_rooms = [
            CalendarRoom(id=rid, name=name, description=desc, capacity=cap, sort_order=order)
            for rid, name, desc, cap, order in DEFAULT_ROOMS
            if rid not in existing_ids
        ]
        if new_rooms:
            db.add_all(new_rooms)
            db.commit()
            max_id = DEFAULT_ROOMS[-1][0]
            db.execute(
                text(
                    f"SELECT setval('calendar_rooms_id_seq', GREATEST({max_id}, "
                    f"(SELECT COALESCE(MAX(id), {max_id}) FROM calendar_rooms)))"
                )
            )
            db.commit()
            logger.info("Default calendar rooms seeded (%d new).", len(new_rooms))
        else:
            logger.info("Calendar rooms already exist (%d).", len(existing_ids))
    finally:
        db.close()


DEFAULT_CATEGORIES = [
    (7, "その他"),
    (8, "OWVIS(ライト)"),
    (9, "OWVIS(旧式)"),
    (10, "OPAS(新規開発)"),
    (11, "OPAS(追加開発)"),
    (12, "OPAS(運用保守)"),
    (13, "OPTAS"),
    (14, "指定伝票"),
    (15, "物流統合PJ"),
    (16, "システム(その他)"),
    (17, "インフラ"),
    (18, "情シス"),
    (19, "社内業務(シス)"),
    (20, "社内業務(ロジ)"),
    (21, "社内業務(BP)"),
    (22, "集荷管理システム"),
]

REMOVED_CATEGORY_IDS = [1, 2, 3, 4, 5, 6]


def seed_default_categories():
    db = SessionLocal()
    try:
        from sqlalchemy import text

        # Remove deprecated categories
        removed = db.query(TaskCategory).filter(TaskCategory.id.in_(REMOVED_CATEGORY_IDS)).all()
        for cat in removed:
            db.delete(cat)
        if removed:
            db.commit()
            logger.info("Removed %d deprecated task categories.", len(removed))

        # Add missing categories
        existing_ids = {row.id for row in db.query(TaskCategory.id).all()}
        new_categories = [
            TaskCategory(id=cat_id, name=name) for cat_id, name in DEFAULT_CATEGORIES if cat_id not in existing_ids
        ]
        if new_categories:
            db.add_all(new_categories)
            db.commit()
            max_id = DEFAULT_CATEGORIES[-1][0]
            db.execute(
                text(
                    f"SELECT setval('task_categories_id_seq', GREATEST({max_id}, "
                    f"(SELECT COALESCE(MAX(id), {max_id}) FROM task_categories)))"
                )
            )
            db.commit()
            logger.info("Task categories seeded (%d new, %d total).", len(new_categories), len(DEFAULT_CATEGORIES))
        else:
            logger.info("Task categories already exist (%d).", len(existing_ids))
    finally:
        db.close()
