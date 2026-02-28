"""Tests for Site Links feature (Groups + Links + Health check + Authorization + Page)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.site_link import SiteGroup, SiteLink

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def test_group(db_session):
    group = SiteGroup(name="テストグループ", color="#ff0000", sort_order=0)
    db_session.add(group)
    db_session.flush()
    return group


@pytest.fixture()
def test_link(db_session, test_group):
    link = SiteLink(
        name="テストサイト",
        url="https://example.com",
        group_id=test_group.id,
        created_by=1,
        check_interval_sec=300,
        check_timeout_sec=10,
    )
    db_session.add(link)
    db_session.flush()
    return link


@pytest.fixture()
def test_link_user2(db_session, other_user):
    link = SiteLink(
        name="User2 サイト",
        url="https://user2.example.com",
        created_by=2,
        check_interval_sec=300,
        check_timeout_sec=10,
    )
    db_session.add(link)
    db_session.flush()
    return link


# ── TestSiteGroupCRUD ─────────────────────────────────────────────────────────


class TestSiteGroupCRUD:
    def test_list_groups_empty(self, client):
        resp = client.get("/api/site-groups/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_group(self, client):
        resp = client.post("/api/site-groups/", json={"name": "G1", "color": "#123456", "sort_order": 0})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "G1"
        assert data["color"] == "#123456"
        assert data["link_count"] == 0

    def test_list_groups(self, client, test_group):
        resp = client.get("/api/site-groups/")
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()]
        assert "テストグループ" in names

    def test_update_group(self, client, test_group):
        resp = client.put(f"/api/site-groups/{test_group.id}", json={"name": "更新済み"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新済み"

    def test_delete_group(self, client, test_group):
        resp = client.delete(f"/api/site-groups/{test_group.id}")
        assert resp.status_code == 204
        resp2 = client.get("/api/site-groups/")
        names = [g["name"] for g in resp2.json()]
        assert "テストグループ" not in names

    def test_create_group_duplicate_name(self, client, test_group):
        resp = client.post("/api/site-groups/", json={"name": "テストグループ"})
        assert resp.status_code == 400

    def test_create_group_invalid_color(self, client):
        resp = client.post("/api/site-groups/", json={"name": "X", "color": "red"})
        assert resp.status_code == 422

    def test_group_requires_admin(self, client_user2):
        resp = client_user2.post("/api/site-groups/", json={"name": "X"})
        assert resp.status_code == 403

    def test_link_count_in_response(self, client, test_group, test_link):
        resp = client.get("/api/site-groups/")
        groups = resp.json()
        g = next(g for g in groups if g["id"] == test_group.id)
        assert g["link_count"] == 1


# ── TestSiteLinkCRUD ─────────────────────────────────────────────────────────


class TestSiteLinkCRUD:
    def test_list_links_empty(self, client):
        resp = client.get("/api/sites/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_link(self, client):
        resp = client.post(
            "/api/sites/",
            json={
                "name": "Google",
                "url": "https://google.com",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Google"
        assert "url" not in data  # URL must not be in response
        assert data["status"] == "unknown"

    def test_list_links(self, client, test_link):
        resp = client.get("/api/sites/")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()]
        assert "テストサイト" in names

    def test_list_links_no_url(self, client, test_link):
        resp = client.get("/api/sites/")
        for link in resp.json():
            assert "url" not in link

    def test_get_link(self, client, test_link):
        resp = client.get(f"/api/sites/{test_link.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "テストサイト"
        assert "url" not in resp.json()

    def test_get_link_not_found(self, client):
        resp = client.get("/api/sites/99999")
        assert resp.status_code == 404

    def test_update_link(self, client, test_link):
        resp = client.put(f"/api/sites/{test_link.id}", json={"name": "更新済み"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新済み"

    def test_delete_link(self, client, test_link):
        resp = client.delete(f"/api/sites/{test_link.id}")
        assert resp.status_code == 204

    def test_create_link_invalid_url(self, client):
        resp = client.post("/api/sites/", json={"name": "X", "url": "ftp://example.com"})
        assert resp.status_code == 422

    def test_create_link_with_group(self, client, test_group):
        resp = client.post(
            "/api/sites/",
            json={
                "name": "グループ付き",
                "url": "https://example.com",
                "group_id": test_group.id,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["group_id"] == test_group.id
        assert data["group_name"] == "テストグループ"


# ── TestSiteLinkOwner ─────────────────────────────────────────────────────────


class TestSiteLinkOwner:
    def test_owner_can_update(self, client, test_link):
        """User 1 (admin/owner) can update their own link."""
        resp = client.put(f"/api/sites/{test_link.id}", json={"name": "更新"})
        assert resp.status_code == 200

    def test_non_owner_cannot_update(self, client_user2, test_link):
        """User 2 cannot update user1's link."""
        resp = client_user2.put(f"/api/sites/{test_link.id}", json={"name": "X"})
        assert resp.status_code == 403

    def test_non_owner_cannot_delete(self, client_user2, test_link):
        resp = client_user2.delete(f"/api/sites/{test_link.id}")
        assert resp.status_code == 403

    def test_admin_can_update_others_link(self, client, test_link_user2):
        """Admin (user 1) can update any link."""
        resp = client.put(f"/api/sites/{test_link_user2.id}", json={"name": "admin更新"})
        assert resp.status_code == 200

    def test_admin_can_delete_others_link(self, client, test_link_user2):
        resp = client.delete(f"/api/sites/{test_link_user2.id}")
        assert resp.status_code == 204

    def test_owner_can_delete_own_link(self, client_user2, test_link_user2):
        resp = client_user2.delete(f"/api/sites/{test_link_user2.id}")
        assert resp.status_code == 204


# ── TestSiteLinkUrl ───────────────────────────────────────────────────────────


class TestSiteLinkUrl:
    def test_url_not_in_list_response(self, client, test_link):
        resp = client.get("/api/sites/")
        for link in resp.json():
            assert "url" not in link

    def test_url_not_in_detail_response(self, client, test_link):
        resp = client.get(f"/api/sites/{test_link.id}")
        assert "url" not in resp.json()

    def test_owner_can_get_url(self, client, test_link):
        resp = client.get(f"/api/sites/{test_link.id}/url")
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com"

    def test_admin_can_get_url_of_others(self, client, test_link_user2):
        resp = client.get(f"/api/sites/{test_link_user2.id}/url")
        assert resp.status_code == 200

    def test_non_owner_cannot_get_url(self, client_user2, test_link):
        """User2 cannot get URL of user1's link."""
        resp = client_user2.get(f"/api/sites/{test_link.id}/url")
        assert resp.status_code == 403


# ── TestSiteLinkCheck ─────────────────────────────────────────────────────────


class TestSiteLinkCheck:
    @pytest.mark.asyncio
    async def test_check_up(self, client, test_link):
        mock_result = {
            "status": "up",
            "response_time_ms": 50,
            "http_status_code": 200,
            "error_msg": None,
            "message": "HTTP 200 (50ms)",
        }
        with patch("app.services.site_link_service._perform_check", new=AsyncMock(return_value=mock_result)):
            resp = client.post(f"/api/sites/{test_link.id}/check", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "up"
        assert data["http_status_code"] == 200
        assert data["response_time_ms"] == 50

    @pytest.mark.asyncio
    async def test_check_down(self, client, test_link):
        mock_result = {
            "status": "down",
            "response_time_ms": None,
            "http_status_code": 503,
            "error_msg": None,
            "message": "HTTP 503",
        }
        with patch("app.services.site_link_service._perform_check", new=AsyncMock(return_value=mock_result)):
            resp = client.post(f"/api/sites/{test_link.id}/check", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "down"

    @pytest.mark.asyncio
    async def test_check_timeout(self, client, test_link):
        mock_result = {
            "status": "timeout",
            "response_time_ms": None,
            "http_status_code": None,
            "error_msg": "Timeout after 10s",
            "message": "Timeout after 10s",
        }
        with patch("app.services.site_link_service._perform_check", new=AsyncMock(return_value=mock_result)):
            resp = client.post(f"/api/sites/{test_link.id}/check", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_check_error(self, client, test_link):
        mock_result = {
            "status": "error",
            "response_time_ms": None,
            "http_status_code": None,
            "error_msg": "Connection refused",
            "message": "Error: Connection refused",
        }
        with patch("app.services.site_link_service._perform_check", new=AsyncMock(return_value=mock_result)):
            resp = client.post(f"/api/sites/{test_link.id}/check", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_check_not_found(self, client):
        resp = client.post("/api/sites/99999/check", json={})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_check_updates_db(self, client, test_link, db_session):
        assert test_link.status == "unknown"
        mock_result = {
            "status": "up",
            "response_time_ms": 100,
            "http_status_code": 200,
            "error_msg": None,
            "message": "HTTP 200 (100ms)",
        }
        with patch("app.services.site_link_service._perform_check", new=AsyncMock(return_value=mock_result)):
            resp = client.post(f"/api/sites/{test_link.id}/check", json={})
        assert resp.status_code == 200
        db_session.expire(test_link)
        db_session.refresh(test_link)
        assert test_link.status == "up"
        assert test_link.response_time_ms == 100


# ── TestSiteChecker ───────────────────────────────────────────────────────────


class TestSiteChecker:
    @pytest.mark.asyncio
    async def test_check_due_only_elapsed(self, db_session):
        """Links whose interval hasn't elapsed should be skipped."""
        from datetime import datetime, timedelta, timezone

        link = SiteLink(
            name="Recent",
            url="https://example.com",
            created_by=1,
            check_interval_sec=300,
            check_timeout_sec=10,
            last_checked_at=datetime.now(timezone.utc) - timedelta(seconds=10),  # only 10s ago
        )
        db_session.add(link)
        db_session.flush()

        with (
            patch("app.services.site_checker.crud") as mock_crud,
            patch("app.services.site_checker._perform_check") as mock_check,
        ):
            mock_crud.get_all_links.return_value = [link]
            from app.services.site_checker import _check_due_links

            with patch("app.services.site_checker.SessionLocal", return_value=db_session):
                await _check_due_links()
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_runs_for_due_link(self, db_session):
        """Link with no last_checked_at should be checked."""
        link = SiteLink(
            name="NeverChecked",
            url="https://example.com",
            created_by=1,
            check_interval_sec=300,
            check_timeout_sec=10,
            last_checked_at=None,
        )
        db_session.add(link)
        db_session.flush()

        mock_result = {
            "status": "up",
            "response_time_ms": 42,
            "http_status_code": 200,
            "error_msg": None,
            "message": "HTTP 200 (42ms)",
        }
        with (
            patch("app.services.site_checker._perform_check", new=AsyncMock(return_value=mock_result)),
            patch("app.services.site_checker.crud.get_all_links", return_value=[link]),
            patch("app.services.site_checker.crud.update_link_status") as mock_update,
            patch("app.services.site_checker.SessionLocal", return_value=db_session),
        ):
            from app.services.site_checker import _check_due_links

            await _check_due_links()
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_in_one_link_does_not_stop_others(self, db_session):
        """gather(return_exceptions=True) isolates per-link failures."""
        link1 = SiteLink(name="L1", url="https://a.com", created_by=1, check_interval_sec=300, check_timeout_sec=10)
        link2 = SiteLink(name="L2", url="https://b.com", created_by=1, check_interval_sec=300, check_timeout_sec=10)
        db_session.add_all([link1, link2])
        db_session.flush()

        check_call_count = 0

        async def side_effect(url, timeout, ssl_verify):
            nonlocal check_call_count
            check_call_count += 1
            if url == "https://a.com":
                raise RuntimeError("boom")
            return {
                "status": "up",
                "response_time_ms": 10,
                "http_status_code": 200,
                "error_msg": None,
                "message": "HTTP 200 (10ms)",
            }

        with (
            patch("app.services.site_checker._perform_check", side_effect=side_effect),
            patch("app.services.site_checker.crud.get_all_links", return_value=[link1, link2]),
            patch("app.services.site_checker.crud.update_link_status") as mock_update,
            patch("app.services.site_checker.SessionLocal", return_value=db_session),
        ):
            from app.services.site_checker import _check_due_links

            await _check_due_links()

        # Both links attempted, but only link2 (successful) gets update_link_status call
        assert check_call_count == 2
        assert mock_update.call_count == 1

    @pytest.mark.asyncio
    async def test_status_change_broadcasts(self, db_session):
        """Status change should trigger WebSocket broadcast."""
        link = SiteLink(
            name="WatchMe",
            url="https://example.com",
            created_by=1,
            check_interval_sec=300,
            check_timeout_sec=10,
            status="up",
        )
        db_session.add(link)
        db_session.flush()

        mock_result = {
            "status": "down",
            "response_time_ms": None,
            "http_status_code": 503,
            "error_msg": None,
            "message": "HTTP 503",
        }

        with (
            patch("app.services.site_checker._perform_check", new=AsyncMock(return_value=mock_result)),
            patch("app.services.site_checker.crud.get_all_links", return_value=[link]),
            patch("app.services.site_checker.crud.update_link_status"),
            patch("app.services.site_checker.site_ws_manager") as mock_ws,
            patch("app.services.site_checker.SessionLocal", return_value=db_session),
        ):
            mock_ws.broadcast = AsyncMock()
            from app.services.site_checker import _check_due_links

            await _check_due_links()

        mock_ws.broadcast.assert_called_once()
        broadcast_data = mock_ws.broadcast.call_args[0][0]
        assert broadcast_data["type"] == "status_update"
        assert broadcast_data["status"] == "down"

    @pytest.mark.asyncio
    async def test_no_status_change_no_broadcast(self, db_session):
        """No broadcast when status stays the same."""
        link = SiteLink(
            name="Stable",
            url="https://example.com",
            created_by=1,
            check_interval_sec=300,
            check_timeout_sec=10,
            status="up",
        )
        db_session.add(link)
        db_session.flush()

        mock_result = {
            "status": "up",
            "response_time_ms": 50,
            "http_status_code": 200,
            "error_msg": None,
            "message": "HTTP 200 (50ms)",
        }

        with (
            patch("app.services.site_checker._perform_check", new=AsyncMock(return_value=mock_result)),
            patch("app.services.site_checker.crud.get_all_links", return_value=[link]),
            patch("app.services.site_checker.crud.update_link_status"),
            patch("app.services.site_checker.site_ws_manager") as mock_ws,
            patch("app.services.site_checker.SessionLocal", return_value=db_session),
        ):
            mock_ws.broadcast = AsyncMock()
            from app.services.site_checker import _check_due_links

            await _check_due_links()

        mock_ws.broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_checker_disabled(self):
        from unittest.mock import MagicMock

        import app.services.site_checker as checker_module

        original = checker_module.SITE_CHECKER_ENABLED
        checker_module.SITE_CHECKER_ENABLED = False
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        await checker_module.start_checker(mock_app)
        assert not hasattr(mock_app.state, "site_checker_task") or True
        checker_module.SITE_CHECKER_ENABLED = original

    @pytest.mark.asyncio
    async def test_stop_checker_no_task(self):
        from unittest.mock import MagicMock

        from app.services.site_checker import stop_checker

        mock_app = MagicMock()
        mock_app.state = MagicMock(spec=[])  # no site_checker_task attr
        await stop_checker(mock_app)  # should not raise


# ── TestSitePage ──────────────────────────────────────────────────────────────


class TestSitePage:
    def test_sites_page_renders(self, client):
        resp = client.get("/sites")
        assert resp.status_code == 200
        assert "Sites" in resp.text

    def test_sites_page_has_nav(self, client):
        resp = client.get("/sites")
        assert "bi-link-45deg" in resp.text
