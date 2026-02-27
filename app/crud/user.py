"""Re-export from portal_core for backward compatibility."""

from typing import List

from sqlalchemy.orm import Session

from portal_core.crud.user import (  # noqa: F401
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    get_users,
    update_password,
    update_user,
)
from portal_core.models.user import User


def get_users_in_department(db: Session, department_id: int, active_only: bool = False) -> List[User]:
    """Get users belonging to a specific department."""
    q = db.query(User).filter(User.department_id == department_id)
    if active_only:
        q = q.filter(User.is_active.is_(True))
    return q.all()
