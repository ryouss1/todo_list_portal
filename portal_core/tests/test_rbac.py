"""Tests for RBAC unification in require_admin (ISSUE-5-05)."""


class TestRequireAdminRBACUnification:
    def test_require_admin_accepts_admin_role(self, client, db_session, test_user):
        """Admin role users pass require_admin."""
        # test_user already has role=admin
        resp = client.get("/api/users/")
        assert resp.status_code == 200

    def test_require_admin_rejects_plain_user(self, client_user2, db_session, other_user):
        """Non-admin users without wildcard permission are rejected by require_admin."""
        resp = client_user2.post(
            "/api/users/",
            json={
                "email": "newuser@example.com",
                "display_name": "New",
                "password": "Password123",
            },
        )
        assert resp.status_code == 403

    def test_require_admin_accepts_wildcard_permission(self, client_user2, db_session, other_user):
        """Non-admin user with wildcard RBAC permission (*:*) passes require_admin."""
        from portal_core.crud.role import assign_user_role, create_role, set_role_permissions
        from portal_core.schemas.role import RoleCreate

        role = create_role(db_session, RoleCreate(name="superuser_rbac", display_name="Super"))
        db_session.flush()
        set_role_permissions(db_session, role.id, [("*", "*", 1)])
        assign_user_role(db_session, other_user.id, role.id)
        db_session.flush()

        # POST /api/users/ requires admin — other_user now has wildcard permission
        resp = client_user2.post(
            "/api/users/",
            json={
                "email": "created_by_rbac@example.com",
                "display_name": "RBAC User",
                "password": "Password123",
            },
        )
        assert resp.status_code == 201


class TestHasPermission:
    def test_has_permission_wildcard_grants_access(self, db_session, test_user):
        """has_permission returns True for any resource:action when user has *:* RBAC permission."""
        from portal_core.crud.role import (
            assign_user_role,
            create_role,
            has_permission,
            set_role_permissions,
        )
        from portal_core.schemas.role import RoleCreate

        role = create_role(db_session, RoleCreate(name="wildcard_tester", display_name="Wildcard"))
        db_session.flush()
        set_role_permissions(db_session, role.id, [("*", "*", 1)])
        assign_user_role(db_session, test_user.id, role.id)
        db_session.flush()

        assert has_permission(db_session, test_user.id, "*", "*") is True
        assert has_permission(db_session, test_user.id, "anything", "delete") is True

    def test_has_permission_false_for_user_without_roles(self, db_session, other_user):
        """has_permission returns False for a user with no RBAC roles assigned."""
        from portal_core.crud.role import has_permission

        result = has_permission(db_session, other_user.id, "*", "*")
        assert result is False
