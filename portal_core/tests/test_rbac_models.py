from portal_core.models.menu import Menu, RoleMenu, UserMenu
from portal_core.models.role import Role, RolePermission, UserRole


def test_role_model_create(db_session):
    role = Role(name="test_role", display_name="Test Role")
    db_session.add(role)
    db_session.flush()
    assert role.id is not None
    assert role.is_active is True
    assert role.sort_order == 0


def test_role_permission_model(db_session):
    role = Role(name="perm_role", display_name="Perm Role")
    db_session.add(role)
    db_session.flush()
    perm = RolePermission(role_id=role.id, resource="users", action="delete", kino_kbn=1)
    db_session.add(perm)
    db_session.flush()
    assert perm.id is not None


def test_user_role_model(db_session, test_user):
    role = Role(name="ur_role", display_name="UR Role")
    db_session.add(role)
    db_session.flush()
    ur = UserRole(user_id=test_user.id, role_id=role.id)
    db_session.add(ur)
    db_session.flush()
    assert ur.id is not None


def test_menu_model_create(db_session):
    menu = Menu(name="test_menu_unique", label="Test Menu", path="/test-menu", icon="bi-gear", sort_order=99)
    db_session.add(menu)
    db_session.flush()
    assert menu.id is not None
    assert menu.is_active is True
    assert menu.required_resource is None


def test_role_menu_model(db_session):
    role = Role(name="rm_role", display_name="RM Role")
    db_session.add(role)
    db_session.flush()
    menu = Menu(name="rm_page", label="RM", path="/rm", sort_order=0)
    db_session.add(menu)
    db_session.flush()
    rm = RoleMenu(role_id=role.id, menu_id=menu.id, kino_kbn=1)
    db_session.add(rm)
    db_session.flush()
    assert rm.role_id is not None
    assert rm.menu_id is not None


def test_user_menu_model(db_session, test_user):
    menu = Menu(name="um_page", label="UM", path="/um", sort_order=0)
    db_session.add(menu)
    db_session.flush()
    um = UserMenu(user_id=test_user.id, menu_id=menu.id, kino_kbn=1)
    db_session.add(um)
    db_session.flush()
    assert um.user_id is not None
    assert um.menu_id is not None
