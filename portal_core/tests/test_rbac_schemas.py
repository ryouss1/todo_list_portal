def test_role_create_schema():
    from portal_core.schemas.role import RoleCreate

    r = RoleCreate(name="admin", display_name="Administrator")
    assert r.name == "admin"
    assert r.sort_order == 0


def test_role_response_from_orm(db_session):
    from portal_core.models.role import Role
    from portal_core.schemas.role import RoleResponse

    role = Role(name="test", display_name="Test", sort_order=0, is_active=True)
    db_session.add(role)
    db_session.flush()
    resp = RoleResponse.model_validate(role)
    assert resp.name == "test"
    assert resp.permissions == []


def test_role_update_schema():
    from portal_core.schemas.role import RoleUpdate

    u = RoleUpdate(display_name="Updated")
    assert u.display_name == "Updated"
    assert u.is_active is None


def test_menu_create_schema():
    from portal_core.schemas.menu import MenuCreate

    m = MenuCreate(name="dash", label="Dashboard", path="/")
    assert m.sort_order == 100
    assert m.required_resource is None


def test_menu_response_from_orm(db_session):
    from portal_core.models.menu import Menu
    from portal_core.schemas.menu import MenuResponse

    menu = Menu(name="test_menu", label="Test", path="/test", sort_order=0)
    db_session.add(menu)
    db_session.flush()
    resp = MenuResponse.model_validate(menu)
    assert resp.name == "test_menu"


def test_permission_item_schema():
    from portal_core.schemas.role import PermissionItem

    p = PermissionItem(resource="reports", action="view")
    assert p.kino_kbn == 1
