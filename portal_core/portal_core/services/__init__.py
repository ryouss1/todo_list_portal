"""Portal core services."""

from portal_core.services.department_service import (
    create_department_svc,
    delete_department_svc,
    get_department_svc,
    get_departments_svc,
    update_department_svc,
)

__all__ = [
    "get_departments_svc",
    "get_department_svc",
    "create_department_svc",
    "update_department_svc",
    "delete_department_svc",
]
