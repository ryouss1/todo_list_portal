# 共通機能分離 フェーズ1・2 実装記録（アーカイブ）

> このファイルは `spec_common_separation.md` から分離した実装記録です。
> フェーズ1・2の全作業が完了（643テスト全パス）。

---

## フェーズ1: 準備リファクタリング ✅ 完了

目的: 分離の前提条件を整える。ディレクトリ移動なし。

| # | 作業 | 詳細 | 影響ファイル |
|---|------|------|------------|
| 1-1 | config.py クラスベース化 | `CoreConfig` + `AppConfig(CoreConfig)` 継承。`globals()` ループで後方互換 | `app/config.py` |
| 1-2 | constants.py 分割 | `UserRole`/`UserRoleType` を core に残し、他6定数を `app/constants.py` に移動 | 9ファイル |
| 1-3 | init_db.py 分割 | `seed_default_user()` を `app/core/init_db.py` に抽出 | 2ファイル |
| 1-4 | base.html ナビ動的化 | 14項目ハードコード → `{% for item in nav_items %}` ループ | `templates/base.html` |
| 1-5 | pages.py ナビ注入 | `_core_nav_items`(2件) + `_app_nav_items`(12件) を `_render()` で注入 | `app/routers/pages.py` |
| 1-6 | models/__init__.py 整理 | コア8モデル / アプリ固有22+モデルをコメント分離 | `app/models/__init__.py` |
| 1-7 | routers/__init__.py 整理 | `_core_routers`(6) / `_app_routers`(16) に分離 | `app/routers/__init__.py` |
| 1-8 | common.js 分離 | `getCategories()` を `static/js/app_common.js` に移動 | 3ファイル |
| 1-9 | テスト確認 | 643テスト全パス | - |

### 実装メモ
- 後方互換: config.py は `globals()` ループ、init_db.py は再エクスポートで既存コードの変更を最小化
- 新規ファイル: `app/constants.py`, `app/core/init_db.py`, `static/js/app_common.js`

---

## フェーズ2: portal_core パッケージ作成 ✅ 完了

目的: `portal_core/` ディレクトリを作成し、共通機能を移動。

| # | 作業 | 詳細 | 影響ファイル |
|---|------|------|------------|
| 2-1 | パッケージ骨格 | `portal_core/pyproject.toml`, `__init__.py` (v0.1.0) | 2ファイル |
| 2-2 | database.py 移動 | `Base`, `SessionLocal`, `engine`, `get_db` → portal_core | 2ファイル |
| 2-3 | 共通モデル8つ移動 | User, Group, LoginAttempt等 → portal_core + app/ shim | 16ファイル |
| 2-4 | core/ 移動 | 19ファイル（exceptions, deps, security, auth/*等） | 19ファイル + shim |
| 2-5 | 共通CRUD 9つ移動 | base, user, group等 → portal_core + shim | 9ファイル + shim |
| 2-6 | 共通スキーマ 4つ移動 | auth, user, group, oauth → portal_core + shim | 4ファイル + shim |
| 2-7 | 共通サービス 7つ移動 | auth, oauth, user, group, email, ws_manager等 | 7ファイル + shim |
| 2-8 | 共通ルーター 4つ移動 | api_auth, api_oauth, api_users, api_groups | 4ファイル + shim |
| 2-9 | PortalApp 実装 | `app_factory.py` (~280行) | 1ファイル |
| 2-10 | テンプレート移動 | base.html, login.html等 6ファイル → portal_core | 6ファイル |
| 2-11 | 静的ファイル移動 | api.js, common.js, style.css等 6ファイル → portal_core | 6ファイル |
| 2-12 | インポートパス修正 | shimで後方互換維持。mock.patchのみ3テストファイル修正 | 3テストファイル |
| 2-13 | models/__init__.py 更新 | コアは portal_core から再エクスポート | 1ファイル |
| 2-14 | main.py 書き換え | PortalApp 方式に完全書き換え | `main.py` |
| 2-15 | Alembic 修正 | `import portal_core.models` 追加 | `alembic/env.py` |
| 2-16 | WS管理 | クラスは portal_core、5インスタンスはapp側に残存 | 2ファイル |
| 2-17 | 静的パス修正 | 共通JS/CSS → `/static/core/xxx` | 2テンプレート |
| 2-18 | テスト確認 | 643テスト全パス（ruff lint/format クリーン） | - |

### 実装メモ
- **再エクスポートshim戦略**: 移動した全ファイルに `app/` shim残置。既存の `from app.xxx import` は全て動作継続
- **テスト修正**: `monkeypatch.setattr()` / `@patch()` はshimではなく実体のportal_coreパスを指定が必要（3ファイル）
- **PortalApp**: `app.state.render` / `app.state.nav_items` / `app.state.config` でアプリ側からアクセス可能
- **pyproject.toml**: isort `known-first-party` に `portal_core` 追加
