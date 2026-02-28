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
