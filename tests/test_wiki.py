"""Tests for WIKI feature (Categories, Tags, Pages, Task Links)."""

import pytest

from app.models.wiki_category import WikiCategory
from app.models.wiki_page import WikiPage
from app.models.wiki_tag import WikiTag


def _collect_tree_ids(nodes: list) -> list:
    """Flatten page IDs from a nested tree response."""
    ids = []
    for node in nodes:
        ids.append(node["id"])
        ids.extend(_collect_tree_ids(node.get("children", [])))
    return ids


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def test_category(db_session):
    cat = WikiCategory(name="テストカテゴリ", color="#6c757d", sort_order=0)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def test_tag(db_session):
    tag = WikiTag(name="テストタグ", slug="test-tag", color="#6c757d", created_by=1)
    db_session.add(tag)
    db_session.flush()
    return tag


@pytest.fixture()
def test_page(db_session, test_category):
    page = WikiPage(
        title="テストページ",
        slug="test-page",
        author_id=1,
        content="",
        visibility="public",
        category_id=test_category.id,
    )
    db_session.add(page)
    db_session.flush()
    return page


@pytest.fixture()
def test_child_page(db_session, test_page):
    child = WikiPage(
        title="子ページ",
        slug="test-child-page",
        author_id=1,
        content="",
        visibility="public",
        parent_id=test_page.id,
    )
    db_session.add(child)
    db_session.flush()
    return child


@pytest.fixture()
def private_page(db_session, test_category):
    """A private page authored by user 1."""
    page = WikiPage(
        title="プライベートページ",
        slug="private-page",
        author_id=1,
        content="",
        visibility="private",
        category_id=test_category.id,
    )
    db_session.add(page)
    db_session.flush()
    return page


# ── TestWikiCategories ─────────────────────────────────────────────────────────


class TestWikiCategories:
    def test_list_categories_empty(self, client):
        resp = client.get("/api/wiki/categories/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_category_requires_admin(self, client_user2):
        resp = client_user2.post("/api/wiki/categories/", json={"name": "テスト", "color": "#123456"})
        assert resp.status_code == 403

    def test_create_category(self, client):
        resp = client.post("/api/wiki/categories/", json={"name": "テストカテゴリX", "color": "#abcdef"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "テストカテゴリX"
        assert data["color"] == "#abcdef"

    def test_create_category_duplicate(self, client, test_category):
        resp = client.post("/api/wiki/categories/", json={"name": "テストカテゴリ"})
        assert resp.status_code == 400

    def test_list_categories_includes_created(self, client, test_category):
        resp = client.get("/api/wiki/categories/")
        names = [c["name"] for c in resp.json()]
        assert "テストカテゴリ" in names

    def test_update_category(self, client, test_category):
        resp = client.put(
            f"/api/wiki/categories/{test_category.id}",
            json={"name": "更新済みカテゴリ"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新済みカテゴリ"

    def test_delete_category(self, client, test_category):
        resp = client.delete(f"/api/wiki/categories/{test_category.id}")
        assert resp.status_code == 204

    def test_delete_category_not_found(self, client):
        resp = client.delete("/api/wiki/categories/999999")
        assert resp.status_code == 404


# ── TestWikiTags ───────────────────────────────────────────────────────────────


class TestWikiTags:
    def test_list_tags_empty(self, client):
        resp = client.get("/api/wiki/tags/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_tag(self, client):
        resp = client.post("/api/wiki/tags/", json={"name": "新しいタグ", "color": "#ff0000"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新しいタグ"
        assert data["slug"]  # slug is auto-generated

    def test_create_tag_duplicate(self, client, test_tag):
        resp = client.post("/api/wiki/tags/", json={"name": "テストタグ"})
        assert resp.status_code == 400

    def test_list_tags_with_q(self, client, test_tag):
        resp = client.get("/api/wiki/tags/?q=テスト")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "テストタグ" in names

    def test_delete_tag_requires_admin(self, client_user2, test_tag):
        resp = client_user2.delete(f"/api/wiki/tags/{test_tag.id}")
        assert resp.status_code == 403

    def test_delete_tag(self, client, test_tag):
        resp = client.delete(f"/api/wiki/tags/{test_tag.id}")
        assert resp.status_code == 204


# ── TestWikiPages ──────────────────────────────────────────────────────────────


class TestWikiPages:
    def test_list_pages_empty(self, client):
        resp = client.get("/api/wiki/pages/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_page(self, client):
        resp = client.post(
            "/api/wiki/pages/",
            json={
                "title": "新規ページ",
                "content": "",
                "visibility": "public",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "新規ページ"
        assert data["slug"]
        assert data["breadcrumbs"] == []

    def test_create_page_with_category_and_tags(self, client, test_category, test_tag):
        resp = client.post(
            "/api/wiki/pages/",
            json={
                "title": "カテゴリ付きページ",
                "content": "",
                "visibility": "public",
                "category_id": test_category.id,
                "tag_ids": [test_tag.id],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["category_id"] == test_category.id
        assert any(t["id"] == test_tag.id for t in data["tags"])

    def test_get_page_by_id(self, client, test_page):
        resp = client.get(f"/api/wiki/pages/{test_page.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == test_page.id
        assert resp.json()["title"] == "テストページ"

    def test_get_page_by_slug(self, client, test_page):
        resp = client.get(f"/api/wiki/pages/by-slug/{test_page.slug}")
        assert resp.status_code == 200
        assert resp.json()["slug"] == test_page.slug

    def test_get_page_not_found(self, client):
        resp = client.get("/api/wiki/pages/999999")
        assert resp.status_code == 404

    def test_get_page_by_slug_not_found(self, client):
        resp = client.get("/api/wiki/pages/by-slug/no-such-page")
        assert resp.status_code == 404

    def test_update_page(self, client, test_page):
        resp = client.put(
            f"/api/wiki/pages/{test_page.id}",
            json={"title": "更新済みタイトル"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "更新済みタイトル"

    def test_update_page_not_owner(self, client_user2, test_page):
        resp = client_user2.put(
            f"/api/wiki/pages/{test_page.id}",
            json={"title": "不正な更新"},
        )
        assert resp.status_code == 403

    def test_delete_page(self, client, test_page):
        resp = client.delete(f"/api/wiki/pages/{test_page.id}")
        assert resp.status_code == 204

    def test_delete_page_not_owner(self, client_user2, test_page):
        resp = client_user2.delete(f"/api/wiki/pages/{test_page.id}")
        assert resp.status_code == 403

    def test_slug_auto_generated(self, client):
        resp = client.post(
            "/api/wiki/pages/",
            json={"title": "日本語タイトルのページ", "visibility": "internal"},
        )
        assert resp.status_code == 201
        assert resp.json()["slug"]  # slug is generated even for Japanese titles

    def test_slug_uniqueness(self, client, test_page):
        # Creating a page with the same slug should produce a different slug
        resp = client.post(
            "/api/wiki/pages/",
            json={"title": "テストページ", "slug": "test-page", "visibility": "internal"},
        )
        assert resp.status_code == 201
        assert resp.json()["slug"] != "test-page"  # appended suffix


# ── TestWikiPageTree ───────────────────────────────────────────────────────────


class TestWikiPageTree:
    def test_tree_empty(self, client):
        resp = client.get("/api/wiki/pages/tree")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tree_with_hierarchy(self, client, test_page, test_child_page):
        resp = client.get("/api/wiki/pages/tree")
        assert resp.status_code == 200
        nodes = resp.json()
        parent = next((n for n in nodes if n["id"] == test_page.id), None)
        assert parent is not None
        assert any(c["id"] == test_child_page.id for c in parent.get("children", []))

    def test_breadcrumbs_for_child(self, client, test_page, test_child_page):
        resp = client.get(f"/api/wiki/pages/{test_child_page.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["breadcrumbs"]) == 1
        assert data["breadcrumbs"][0]["id"] == test_page.id


# ── TestWikiPageMove ───────────────────────────────────────────────────────────


class TestWikiPageMove:
    def test_move_page_under_parent(self, client, test_page, test_child_page):
        # Create another root page and move it under test_page
        resp = client.post(
            "/api/wiki/pages/",
            json={"title": "移動対象ページ", "visibility": "internal"},
        )
        page_id = resp.json()["id"]

        resp = client.put(
            f"/api/wiki/pages/{page_id}/move",
            json={"parent_id": test_page.id, "sort_order": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["parent_id"] == test_page.id

    def test_move_page_circular_reference(self, client, test_page, test_child_page):
        # Cannot move parent under its own child
        resp = client.put(
            f"/api/wiki/pages/{test_page.id}/move",
            json={"parent_id": test_child_page.id},
        )
        assert resp.status_code == 400

    def test_move_page_self_parent(self, client, test_page):
        resp = client.put(
            f"/api/wiki/pages/{test_page.id}/move",
            json={"parent_id": test_page.id},
        )
        assert resp.status_code == 400


# ── TestWikiPageFilter ─────────────────────────────────────────────────────────


class TestWikiPageFilter:
    def test_filter_by_category(self, client, test_page, test_category):
        resp = client.get(f"/api/wiki/pages/?category_id={test_category.id}")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert test_page.id in ids

    def test_filter_by_tag_slug(self, client, test_page, test_tag, db_session):
        # Attach tag to page
        from app.crud import wiki_tag as tag_crud

        tag_crud.update_page_tags(db_session, test_page, [test_tag.id])
        db_session.flush()

        resp = client.get(f"/api/wiki/pages/?tag_slug={test_tag.slug}")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert test_page.id in ids


# ── TestWikiPageTags ───────────────────────────────────────────────────────────


class TestWikiPageTags:
    def test_update_page_tags(self, client, test_page, test_tag):
        resp = client.put(
            f"/api/wiki/pages/{test_page.id}/tags",
            json={"tag_ids": [test_tag.id]},
        )
        assert resp.status_code == 200
        assert any(t["id"] == test_tag.id for t in resp.json()["tags"])

    def test_clear_page_tags(self, client, test_page, test_tag, db_session):
        from app.crud import wiki_tag as tag_crud

        tag_crud.update_page_tags(db_session, test_page, [test_tag.id])
        db_session.flush()

        resp = client.put(
            f"/api/wiki/pages/{test_page.id}/tags",
            json={"tag_ids": []},
        )
        assert resp.status_code == 200
        assert resp.json()["tags"] == []


# ── TestWikiPages (page routes) ────────────────────────────────────────────────


class TestWikiPageRoutes:
    def test_wiki_list_page(self, client):
        resp = client.get("/wiki")
        assert resp.status_code == 200

    def test_wiki_new_page(self, client):
        resp = client.get("/wiki/new")
        assert resp.status_code == 200

    def test_wiki_page_view(self, client, test_page):
        resp = client.get(f"/wiki/{test_page.slug}")
        assert resp.status_code == 200

    def test_wiki_edit_page(self, client, test_page):
        resp = client.get(f"/wiki/{test_page.slug}/edit")
        assert resp.status_code == 200


# ── TestWikiVisibility ─────────────────────────────────────────────────────────


class TestWikiVisibility:
    """Visibility filter for list/tree endpoints.

    Visibility values:
      public  – 他部署: all authenticated users
      local   – 自部署: same group as page author
      private – 非公開: author only
    """

    def test_private_page_visible_to_owner_in_list(self, client, private_page):
        resp = client.get("/api/wiki/pages/")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert private_page.id in ids

    def test_private_page_hidden_from_other_user_in_list(self, client_user2, private_page):
        resp = client_user2.get("/api/wiki/pages/")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert private_page.id not in ids

    def test_private_page_visible_to_owner_in_tree(self, client, private_page):
        resp = client.get("/api/wiki/pages/tree")
        assert resp.status_code == 200
        assert private_page.id in _collect_tree_ids(resp.json())

    def test_private_page_hidden_from_other_user_in_tree(self, client_user2, private_page):
        resp = client_user2.get("/api/wiki/pages/tree")
        assert resp.status_code == 200
        assert private_page.id not in _collect_tree_ids(resp.json())

    def test_public_page_visible_to_all_authenticated(self, client_user2, test_page):
        # test_page has visibility="public" → visible to all authenticated users
        resp = client_user2.get("/api/wiki/pages/")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert test_page.id in ids

    def test_local_page_visible_to_owner(self, client, db_session, test_category):
        """local page is visible to its author."""
        page = WikiPage(
            title="自部署ページ",
            slug="local-page-owner",
            author_id=1,
            content="",
            visibility="local",
            category_id=test_category.id,
        )
        db_session.add(page)
        db_session.flush()

        resp = client.get("/api/wiki/pages/")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert page.id in ids

    def test_local_page_hidden_from_user_without_same_group(self, client_user2, db_session, test_category):
        """local page by user1 (no group) is hidden from user2 (no group)."""
        page = WikiPage(
            title="自部署ページ（他者非表示）",
            slug="local-page-hidden",
            author_id=1,
            content="",
            visibility="local",
            category_id=test_category.id,
        )
        db_session.add(page)
        db_session.flush()

        resp = client_user2.get("/api/wiki/pages/")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert page.id not in ids


# ── TestWikiTaskLinkPermissions ────────────────────────────────────────────────


class TestWikiTaskLinkPermissions:
    """ISSUE-2-02 + ISSUE-2-15: Task link authorization checks."""

    def test_add_task_link_forbidden_for_non_owner(self, client_user2, test_page):
        resp = client_user2.post(f"/api/wiki/pages/{test_page.id}/tasks/999")
        assert resp.status_code == 403

    def test_remove_task_link_forbidden_for_non_owner(self, client_user2, test_page):
        resp = client_user2.delete(f"/api/wiki/pages/{test_page.id}/tasks/999")
        assert resp.status_code == 403

    def test_update_task_item_links_forbidden_for_non_owner(self, client_user2, test_page):
        resp = client_user2.put(
            f"/api/wiki/pages/{test_page.id}/tasks/task-items",
            json={"task_item_ids": []},
        )
        assert resp.status_code == 403


# ── TestWikiSlug ───────────────────────────────────────────────────────────────


class TestWikiSlugGeneration:
    """ISSUE-2-09: Slug max length check."""

    def test_long_title_slug_is_truncated(self, client):
        # 500 'a' chars → title fits in DB (String(500)), slug gets truncated to ≤480
        long_title = "a" * 500
        resp = client.post(
            "/api/wiki/pages/",
            json={"title": long_title, "visibility": "internal"},
        )
        assert resp.status_code == 201
        assert len(resp.json()["slug"]) <= 480


class TestPagination:
    def test_list_pages_limit(self, client, db_session):
        """GET /api/wiki/pages/ should support limit parameter."""
        from app.models.wiki_page import WikiPage

        for i in range(5):
            db_session.add(
                WikiPage(
                    title=f"Page {i}",
                    slug=f"page-{i}-pagination",
                    author_id=1,
                    visibility="public",
                )
            )
        db_session.flush()

        resp = client.get("/api/wiki/pages/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2
