"""Core seed functions for portal_core."""

import logging

from portal_core.config import DEFAULT_DISPLAY_NAME, DEFAULT_EMAIL, DEFAULT_PASSWORD, DEFAULT_USER_ID
from portal_core.core.security import hash_password
from portal_core.database import SessionLocal

logger = logging.getLogger("portal_core.init_db")


def seed_default_user():
    from portal_core.models.user import User

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


def seed_default_roles(db=None):
    """Seed system_admin role with wildcard permissions. Idempotent."""
    from portal_core.models.role import Role, RolePermission

    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        admin_role = db.query(Role).filter(Role.name == "system_admin").first()
        if not admin_role:
            admin_role = Role(
                name="system_admin",
                display_name="システム管理者",
                description="全権限を持つシステム管理者ロール",
                sort_order=0,
            )
            db.add(admin_role)
            db.flush()
            logger.info("system_admin role created.")

        wildcard = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == admin_role.id,
                RolePermission.resource == "*",
                RolePermission.action == "*",
            )
            .first()
        )
        if not wildcard:
            db.add(
                RolePermission(
                    role_id=admin_role.id,
                    resource="*",
                    action="*",
                    kino_kbn=1,
                )
            )
            logger.info("system_admin wildcard permission created.")

        if close_after:
            db.commit()
    finally:
        if close_after:
            db.close()
