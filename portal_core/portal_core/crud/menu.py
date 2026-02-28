from typing import List, Optional

from sqlalchemy.orm import Session

from portal_core.core.constants import UserRole as UserRoleEnum
from portal_core.models.menu import Menu, RoleMenu, UserMenu
from portal_core.models.user import User
from portal_core.schemas.menu import MenuCreate, MenuUpdate


def create_menu(db: Session, data: MenuCreate) -> Menu:
    menu = Menu(**data.model_dump())
    db.add(menu)
    return menu


def get_menu(db: Session, menu_id: int) -> Optional[Menu]:
    return db.query(Menu).filter(Menu.id == menu_id).first()


def get_menu_by_name(db: Session, name: str) -> Optional[Menu]:
    return db.query(Menu).filter(Menu.name == name).first()


def get_menus(db: Session) -> List[Menu]:
    return db.query(Menu).order_by(Menu.sort_order, Menu.name).all()


def update_menu(db: Session, menu_id: int, data: MenuUpdate) -> Optional[Menu]:
    menu = get_menu(db, menu_id)
    if not menu:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)
    return menu


def delete_menu(db: Session, menu_id: int) -> None:
    db.query(RoleMenu).filter(RoleMenu.menu_id == menu_id).delete()
    db.query(UserMenu).filter(UserMenu.menu_id == menu_id).delete()
    db.query(Menu).filter(Menu.id == menu_id).delete()


def get_visible_menus_for_user(db: Session, user_id: int) -> List[Menu]:
    """Return menus visible to the user based on permissions.

    Visibility priority:
    1. Per-user UserMenu override (highest)
    2. No restriction required = visible to all authenticated users
    3. Admin legacy role bypass
    4. Role-based permission (required_resource + required_action)
    """
    from portal_core.crud.role import has_permission

    user = db.query(User).filter(User.id == user_id).first()
    is_admin = user and user.role == UserRoleEnum.ADMIN

    all_menus = db.query(Menu).filter(Menu.is_active.is_(True)).order_by(Menu.sort_order, Menu.name).all()

    # Pre-fetch user overrides for efficiency
    user_overrides = {um.menu_id: um.kino_kbn for um in db.query(UserMenu).filter(UserMenu.user_id == user_id).all()}

    visible = []
    for menu in all_menus:
        # 1. Per-user override takes precedence
        if menu.id in user_overrides:
            if user_overrides[menu.id] == 1:
                visible.append(menu)
            continue

        # 2. No restriction = visible to all
        if menu.required_resource is None:
            visible.append(menu)
            continue

        # 3. Admin bypass
        if is_admin:
            visible.append(menu)
            continue

        # 4. Check role-based permission
        required_action = menu.required_action or "view"
        if has_permission(db, user_id, menu.required_resource, required_action):
            visible.append(menu)

    return visible


def upsert_menu_from_nav_item(
    db: Session,
    name: str,
    label: str,
    path: str,
    icon: str,
    sort_order: int,
    badge_id: Optional[str] = None,
    required_resource: Optional[str] = None,
    required_action: Optional[str] = None,
) -> Menu:
    """Upsert a menu item from a NavItem (called at startup to sync in-memory nav to DB)."""
    existing = db.query(Menu).filter(Menu.name == name).first()
    if existing:
        existing.label = label
        existing.path = path
        existing.icon = icon
        existing.sort_order = sort_order
        existing.badge_id = badge_id
        existing.required_resource = required_resource
        existing.required_action = required_action
        return existing
    menu = Menu(
        name=name,
        label=label,
        path=path,
        icon=icon,
        sort_order=sort_order,
        badge_id=badge_id,
        required_resource=required_resource,
        required_action=required_action,
    )
    db.add(menu)
    return menu
