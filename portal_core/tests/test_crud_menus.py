def test_create_and_get_menu(db_session):
    from portal_core.crud.menu import create_menu, get_menu
    from portal_core.schemas.menu import MenuCreate

    menu = create_menu(db_session, MenuCreate(name="dash2", label="Dashboard", path="/"))
    db_session.flush()
    fetched = get_menu(db_session, menu.id)
    assert fetched.name == "dash2"


def test_menu_without_restriction_visible_to_all(db_session, test_user):
    from portal_core.crud.menu import create_menu, get_visible_menus_for_user
    from portal_core.schemas.menu import MenuCreate

    create_menu(db_session, MenuCreate(name="public_page", label="Public", path="/public", sort_order=0))
    db_session.flush()
    menus = get_visible_menus_for_user(db_session, test_user.id)
    assert any(m.name == "public_page" for m in menus)


def test_admin_bypass_grants_restricted_menu(db_session, test_user):
    from portal_core.crud.menu import create_menu, get_visible_menus_for_user
    from portal_core.schemas.menu import MenuCreate

    create_menu(
        db_session,
        MenuCreate(
            name="admin_only_page",
            label="Admin",
            path="/admin",
            required_resource="admin_panel",
            required_action="view",
            sort_order=0,
        ),
    )
    db_session.flush()
    menus = get_visible_menus_for_user(db_session, test_user.id)
    # test_user has role=admin, so the admin bypass applies and the
    # restricted menu is visible even without an explicit role permission
    assert any(m.name == "admin_only_page" for m in menus)


def test_menu_hidden_for_regular_user(db_session, other_user):
    from portal_core.crud.menu import create_menu, get_visible_menus_for_user
    from portal_core.schemas.menu import MenuCreate

    create_menu(
        db_session,
        MenuCreate(
            name="restricted_menu",
            label="Restricted",
            path="/restricted",
            required_resource="reports",
            required_action="manage",
            sort_order=0,
        ),
    )
    db_session.flush()
    # other_user has no role and is not admin
    menus = get_visible_menus_for_user(db_session, other_user.id)
    assert not any(m.name == "restricted_menu" for m in menus)


def test_user_menu_override_grants_access(db_session, other_user):
    from portal_core.crud.menu import create_menu, get_visible_menus_for_user
    from portal_core.models.menu import UserMenu
    from portal_core.schemas.menu import MenuCreate

    menu = create_menu(
        db_session,
        MenuCreate(
            name="override_menu",
            label="Override",
            path="/override",
            required_resource="reports",
            required_action="manage",
            sort_order=0,
        ),
    )
    db_session.flush()
    # Grant per-user override
    db_session.add(UserMenu(user_id=other_user.id, menu_id=menu.id, kino_kbn=1))
    db_session.flush()
    menus = get_visible_menus_for_user(db_session, other_user.id)
    assert any(m.name == "override_menu" for m in menus)


def test_user_menu_override_denies_access(db_session, test_user):
    from portal_core.crud.menu import create_menu, get_visible_menus_for_user
    from portal_core.models.menu import UserMenu
    from portal_core.schemas.menu import MenuCreate

    # Create an unrestricted menu (normally visible to all)
    menu = create_menu(db_session, MenuCreate(name="deny_override_menu", label="Deny", path="/deny", sort_order=0))
    db_session.flush()
    # Add explicit deny override for test_user (who is admin)
    db_session.add(UserMenu(user_id=test_user.id, menu_id=menu.id, kino_kbn=0))
    db_session.flush()
    menus = get_visible_menus_for_user(db_session, test_user.id)
    # Even though user is admin and menu has no restriction, override denies it
    assert not any(m.name == "deny_override_menu" for m in menus)


def test_upsert_menu_from_nav_item(db_session):
    from portal_core.crud.menu import get_menus, upsert_menu_from_nav_item

    upsert_menu_from_nav_item(db_session, "nav_item", "Nav Item", "/nav", "bi-x", sort_order=50)
    db_session.flush()
    menus = get_menus(db_session)
    assert any(m.name == "nav_item" for m in menus)
    # Upsert again = no duplicate
    upsert_menu_from_nav_item(db_session, "nav_item", "Nav Item Updated", "/nav", "bi-x", sort_order=50)
    db_session.flush()
    assert len([m for m in get_menus(db_session) if m.name == "nav_item"]) == 1
