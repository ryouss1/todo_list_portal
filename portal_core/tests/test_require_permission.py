def test_require_permission_allows_legacy_admin(client, db_session):
    """Legacy admin (user.role == 'admin') can access any require_permission endpoint."""
    # client fixture is admin via legacy role
    r = client.get("/api/roles/")
    assert r.status_code == 200


def test_require_permission_blocks_user_without_permission(db_session, other_user, client_user2):
    """User without the required permission is blocked by require_permission."""
    # other_user has no roles assigned, so has no permissions
    # GET /api/roles/ requires 'roles:read' or admin
    r = client_user2.get("/api/roles/")
    assert r.status_code == 403


def test_require_permission_blocks_unauthenticated(raw_client):
    r = raw_client.get("/api/roles/")
    assert r.status_code in (401, 403)
