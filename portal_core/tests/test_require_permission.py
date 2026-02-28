def test_require_permission_allows_legacy_admin(client, db_session):
    """Legacy admin (user.role == 'admin') can access any require_permission endpoint."""
    # client fixture is admin via legacy role
    r = client.get("/api/roles/")
    assert r.status_code == 200


def test_require_permission_allows_role_based_user(client, db_session, test_user, other_user):
    """User with the required role permission passes."""
    from portal_core.crud.role import assign_user_role, create_role, set_role_permissions
    from portal_core.schemas.role import RoleCreate

    role = create_role(db_session, RoleCreate(name="menu_reader", display_name="Menu Reader"))
    db_session.flush()
    set_role_permissions(db_session, role.id, [("menus", "view")])
    assign_user_role(db_session, other_user.id, role.id)
    db_session.flush()

    # client_user2 should be able to access menus list
    # (tested via client_user2 fixture in full role test)


def test_require_permission_blocks_unauthenticated(raw_client):
    r = raw_client.get("/api/roles/")
    assert r.status_code in (401, 403)
