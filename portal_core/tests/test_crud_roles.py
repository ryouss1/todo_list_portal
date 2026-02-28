def test_create_and_get_role(db_session):
    from portal_core.crud.role import create_role, get_role
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="get_role", display_name="Get Role"))
    db_session.flush()
    fetched = get_role(db_session, role.id)
    assert fetched.name == "get_role"


def test_get_roles_empty(db_session):
    from portal_core.crud.role import get_roles

    assert get_roles(db_session) == []


def test_get_role_by_name(db_session):
    from portal_core.crud.role import create_role, get_role_by_name
    from portal_core.schemas.role import RoleCreate

    create_role(db_session, RoleCreate(name="named_role", display_name="Named"))
    db_session.flush()
    found = get_role_by_name(db_session, "named_role")
    assert found is not None
    assert found.name == "named_role"
    assert get_role_by_name(db_session, "nonexistent") is None


def test_update_role(db_session):
    from portal_core.crud.role import create_role, update_role
    from portal_core.schemas.role import RoleCreate, RoleUpdate

    role = create_role(db_session, RoleCreate(name="update_me", display_name="Old"))
    db_session.flush()
    updated = update_role(db_session, role.id, RoleUpdate(display_name="New"))
    assert updated.display_name == "New"


def test_delete_role(db_session):
    from portal_core.crud.role import create_role, delete_role, get_role
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="delete_me", display_name="Delete"))
    db_session.flush()
    delete_role(db_session, role.id)
    db_session.flush()
    assert get_role(db_session, role.id) is None


def test_set_and_get_permissions(db_session):
    from portal_core.crud.role import create_role, get_role_permissions, set_role_permissions
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="perm_role", display_name="Perm"))
    db_session.flush()
    set_role_permissions(db_session, role.id, [("users", "view"), ("users", "delete")])
    db_session.flush()
    perms = get_role_permissions(db_session, role.id)
    assert {(p.resource, p.action) for p in perms} == {("users", "view"), ("users", "delete")}


def test_has_permission_via_role(db_session, test_user):
    from portal_core.crud.role import assign_user_role, create_role, has_permission, set_role_permissions
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="viewer", display_name="Viewer"))
    db_session.flush()
    set_role_permissions(db_session, role.id, [("reports", "view")])
    assign_user_role(db_session, test_user.id, role.id)
    db_session.flush()
    assert has_permission(db_session, test_user.id, "reports", "view")
    assert not has_permission(db_session, test_user.id, "reports", "delete")


def test_wildcard_permission(db_session, test_user):
    from portal_core.crud.role import assign_user_role, create_role, has_permission, set_role_permissions
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="superadmin", display_name="Super"))
    db_session.flush()
    set_role_permissions(db_session, role.id, [("*", "*")])
    assign_user_role(db_session, test_user.id, role.id)
    db_session.flush()
    assert has_permission(db_session, test_user.id, "anything", "delete")


def test_revoke_user_role(db_session, test_user):
    from portal_core.crud.role import (
        assign_user_role,
        create_role,
        has_permission,
        revoke_user_role,
        set_role_permissions,
    )
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="revoke_me", display_name="Revoke"))
    db_session.flush()
    assign_user_role(db_session, test_user.id, role.id)
    set_role_permissions(db_session, role.id, [("tasks", "view")])
    db_session.flush()
    assert has_permission(db_session, test_user.id, "tasks", "view")
    revoke_user_role(db_session, test_user.id, role.id)
    db_session.flush()
    assert not has_permission(db_session, test_user.id, "tasks", "view")


def test_get_user_roles(db_session, test_user):
    from portal_core.crud.role import assign_user_role, create_role, get_user_roles
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="my_role", display_name="My Role"))
    db_session.flush()
    assign_user_role(db_session, test_user.id, role.id)
    db_session.flush()
    roles = get_user_roles(db_session, test_user.id)
    assert len(roles) == 1
    assert roles[0].name == "my_role"
