import logging

from app.config import DEFAULT_DISPLAY_NAME, DEFAULT_EMAIL, DEFAULT_PASSWORD, DEFAULT_USER_ID
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import User
from app.models.attendance_preset import AttendancePreset
from app.models.calendar_room import CalendarRoom
from app.models.group import Group
from app.models.task_category import TaskCategory

logger = logging.getLogger("app.init_db")


def seed_default_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
        if not user:
            user = User(
                id=DEFAULT_USER_ID,
                email=DEFAULT_EMAIL,
                display_name=DEFAULT_DISPLAY_NAME,
                password_hash=hash_password(DEFAULT_PASSWORD),
                role="admin",
            )
            db.add(user)
            db.commit()
            logger.info("Default user '%s' created with admin role.", DEFAULT_DISPLAY_NAME)
        else:
            changed = False
            if not user.password_hash:
                user.password_hash = hash_password(DEFAULT_PASSWORD)
                changed = True
                logger.info("Default user password_hash set.")
            if user.role != "admin":
                user.role = "admin"
                changed = True
                logger.info("Default user role set to admin.")
            if user.email != DEFAULT_EMAIL:
                user.email = DEFAULT_EMAIL
                changed = True
                logger.info("Default user email updated to %s.", DEFAULT_EMAIL)
            if changed:
                db.commit()
            logger.info("Default user already exists.")
    finally:
        db.close()


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


DEFAULT_GROUPS = [
    (1, "開発チーム", "ソフトウェア開発", 1),
    (2, "営業チーム", "営業・顧客対応", 2),
    (3, "管理部", "総務・経理", 3),
]


def seed_default_groups():
    db = SessionLocal()
    try:
        from sqlalchemy import text

        existing_ids = {row.id for row in db.query(Group.id).all()}
        new_groups = [
            Group(id=gid, name=name, description=desc, sort_order=order)
            for gid, name, desc, order in DEFAULT_GROUPS
            if gid not in existing_ids
        ]
        if new_groups:
            db.add_all(new_groups)
            db.commit()
            max_id = DEFAULT_GROUPS[-1][0]
            db.execute(
                text(
                    f"SELECT setval('groups_id_seq', GREATEST({max_id}, "
                    f"(SELECT COALESCE(MAX(id), {max_id}) FROM groups)))"
                )
            )
            db.commit()
            logger.info("Default groups seeded (%d new).", len(new_groups))
        else:
            logger.info("Groups already exist (%d).", len(existing_ids))
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
