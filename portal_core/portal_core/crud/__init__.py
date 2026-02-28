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
from portal_core.crud.menu import create_menu as create_menu
from portal_core.crud.menu import delete_menu as delete_menu
from portal_core.crud.menu import get_menu as get_menu
from portal_core.crud.menu import get_menu_by_name as get_menu_by_name
from portal_core.crud.menu import get_menus as get_menus
from portal_core.crud.menu import get_visible_menus_for_user as get_visible_menus_for_user
from portal_core.crud.menu import update_menu as update_menu
from portal_core.crud.menu import upsert_menu_from_nav_item as upsert_menu_from_nav_item

__all__ = [
    "count_department_members",
    "create_department",
    "delete_department",
    "get_department",
    "get_departments",
    "get_departments_active",
    "update_department",
    "create_menu",
    "delete_menu",
    "get_menu",
    "get_menu_by_name",
    "get_menus",
    "get_visible_menus_for_user",
    "update_menu",
    "upsert_menu_from_nav_item",
]
