def test_seed_default_roles_creates_system_admin(db_session):
    from portal_core.init_db import seed_default_roles

    seed_default_roles(db_session)
    from portal_core.models.role import Role, RolePermission

    role = db_session.query(Role).filter(Role.name == "system_admin").first()
    assert role is not None
    wildcard = (
        db_session.query(RolePermission)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.resource == "*",
            RolePermission.action == "*",
        )
        .first()
    )
    assert wildcard is not None


def test_seed_default_roles_idempotent(db_session):
    from portal_core.init_db import seed_default_roles

    seed_default_roles(db_session)
    seed_default_roles(db_session)  # call twice
    from portal_core.models.role import Role

    count = db_session.query(Role).filter(Role.name == "system_admin").count()
    assert count == 1


def test_seed_menus_from_nav_items(db_session):
    from portal_core.crud.menu import get_menus, upsert_menu_from_nav_item

    upsert_menu_from_nav_item(db_session, "dashboard", "Dashboard", "/", "bi-speedometer2", sort_order=0)
    upsert_menu_from_nav_item(db_session, "users_admin", "Users", "/users", "bi-people-fill", sort_order=900)
    db_session.flush()
    menus = get_menus(db_session)
    names = {m.name for m in menus}
    assert "dashboard" in names
    assert "users_admin" in names
