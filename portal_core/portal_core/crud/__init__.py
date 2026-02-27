"""Portal core CRUD modules."""

from portal_core.crud.department import (
    count_members as count_department_members,
)
from portal_core.crud.department import (
    create_department as create_department,
)
from portal_core.crud.department import (
    delete_department as delete_department,
)
from portal_core.crud.department import (
    get_department as get_department,
)
from portal_core.crud.department import (
    get_departments as get_departments,
)
from portal_core.crud.department import (
    get_departments_active as get_departments_active,
)
from portal_core.crud.department import (
    update_department as update_department,
)

__all__ = [
    "count_department_members",
    "create_department",
    "delete_department",
    "get_department",
    "get_departments",
    "get_departments_active",
    "update_department",
]
