# 共通機能分離 設計書

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。
> 作成日: 2026-02-22 / 更新日: 2026-02-24

**フェーズ状況:**

| フェーズ | 作業数 | 状態 |
|---------|-------|------|
| フェーズ1: 準備リファクタリング | 9作業 | ✅ 完了 |
| フェーズ2: portal_core パッケージ作成 | 18作業 | ✅ 完了 |
| フェーズ3: テスト分離・安定化 | 11作業 | ✅ 完了（コア151 + アプリ500 = 651テスト） |

**アーカイブ（完了済みフェーズの詳細）:**
- [フェーズ1・2 実装記録](./archive/spec_common_separation_phase1_2.md)
- [設計詳細・FAQ](./archive/spec_common_separation_design.md)

---

## 1. コンセプト概要

**`portal_core` は認証込みで単体稼働する完成品。**

- `portal_core` 単体 → ログイン画面・ユーザー管理・グループ管理が動くWebアプリ
- 業務機能（Todo、勤怠等）は `portal_core` の上に追加するイメージ
- エントリーポイント: `PortalApp(config).setup_core()` → `register_*()` → `build()`

**現在のファイル構造:**

```
portal_core/                        # pip パッケージ (pip install -e portal_core/)
├── pyproject.toml
└── portal_core/
    ├── __init__.py                 # v0.1.0
    ├── app_factory.py              # ★ PortalApp + NavItem (~420 lines)
    ├── config.py                   # CoreConfig
    ├── database.py                 # Base, SessionLocal, engine, get_db
    ├── init_db.py                  # seed_default_user
    ├── core/                       # 19 files (exceptions, deps, security, auth/*, etc.)
    ├── models/                     # 8 models + __init__.py
    ├── crud/                       # 9 CRUD + __init__.py
    ├── schemas/                    # 4 schemas + __init__.py
    ├── services/                   # 7 services + __init__.py
    ├── routers/                    # 4 routers + __init__.py
    ├── templates/                  # 6 templates (base, login, users, forgot/reset_password, _dashboard_base)
    └── static/                     # 6 files (→ /static/core/)

app/                                # アプリ固有 + 再エクスポートshim
├── config.py                       # AppConfig(CoreConfig) + globals() compat
├── constants.py                    # App-specific constants
├── database.py                     # shim → portal_core.database
├── models/__init__.py              # Core re-export + App models (22+)
├── routers/                        # App routers only (16) + pages.py
└── services/websocket_manager.py   # WS class re-export + 4 singleton instances

main.py                             # PortalApp(config).setup_core() → register_*() → build()
```

**設計原則:**
- 後方互換: `app/` 配下に再エクスポートshimを配置、既存の `from app.xxx import` は全て動作継続
- 静的ファイル: コア → `/static/core/`、アプリ固有 → `/static/`
- テンプレート: portal_core がマスター（base, login, users, forgot/reset_password）、アプリ側は業務ページ（14ファイル）のみ。Jinja2 の検索順はアプリ側 `templates/` → コア `portal_core/portal_core/templates/`
- ブランド動的化: テンプレート内の `{{ app_title }}` は `_render()` が `self.title` から自動注入
- `register_head_script(path)`: アプリ固有のグローバルスクリプトを `base.html` の `<head>` に注入する API
- `monkeypatch`/`mock.patch`: shimではなく実体の `portal_core.*` パスを指定が必要

---

## 2. 技術的負債（残存）

| 項目 | 現状 | 対応フェーズ |
|------|------|------------|
| テストフィクスチャの密結合 | ✅ 解消。portal_core/tests/conftest.py（core_app フィクスチャ）とtests/conftest.py（from main import app）に分離 | フェーズ3 |
| テンプレート重複 | ✅ 解消。portal_core テンプレートをマスター化、アプリ側の重複5ファイル削除、`{{ app_title }}` + `register_head_script()` で動的化 | フェーズ3後 |
| WebSocket DI化が不完全 | WS クラスは portal_core、5インスタンスはアプリ側に残存。サービスからの直接インポートを shim 経由で維持 | 将来 |
| Tasks→Reports の暗黙的依存 | Done時の日報自動作成がサービス間直接呼び出し | 将来（イベントバス） |
| 翻訳ファイルの分離 | 共通キーとアプリ固有キーが混在（translations/, static/locale/）。portal_core テストは editable install 経由でプロジェクトルートの翻訳ファイルを参照 | 将来 |

---

## 3. 残存課題

### P-1: サービス間の密結合（Task → DailyReport）

`task_service.done_task()` が `daily_report` の CRUD・モデル・スキーマを直接インポート。Task と Report を別アプリに分離できない。

**対処:** 当面は同一アプリ内に同居を強制。将来的にコールバック/フック方式に変更可能。

### P-6: テストフィクスチャの分離 → ✅ フェーズ3で解消

portal_core/tests/conftest.py（`core_app` フィクスチャ）と tests/conftest.py（`from main import app`）に分離済み。

### P-8: WebSocketManager のインスタンス管理

クラスは portal_core に移動済みだが、5インスタンスがアプリ側で直接インポートされている。DI化は将来課題。

### P-9: 翻訳ファイルの分割

翻訳ファイルに共通キーとアプリ固有キーが混在。フェーズ3では分離せず、portal_core テストがプロジェクトルートの翻訳を参照する暫定措置。

---

## 4. フェーズ3: テスト分離・安定化

目的: portal_core 単体テストを確立し、アプリ側テストとの分離を完成させる。

### 4.A 現状分析

**テストファイル一覧（26ファイル、651テスト — 分離後: コア151 + アプリ500）:**

| 分類 | ファイル | テスト数 | 行数 | 移動先 |
|------|---------|---------|------|--------|
| **コア** | test_auth.py | 12 | 72 | portal_core/tests/ |
| **コア** | test_auth_security.py | 27 | 301 | portal_core/tests/ |
| **コア** | test_oauth.py | 22 | 402 | portal_core/tests/ |
| **コア** | test_password_reset.py | 23 | 312 | portal_core/tests/ |
| **コア** | test_users.py | 28 | 213 | portal_core/tests/ |
| **コア** | test_groups.py | 11 | 131 | portal_core/tests/ |
| **コア** | test_websocket.py | 4 | 48 | portal_core/tests/ |
| **コア** | test_i18n.py | 17 | 214 | portal_core/tests/ |
| **コア小計** | | **144** | **1,693** | |
| アプリ | (18ファイル) | ~500 | 7,144 | 残留 |

**特記事項:**
- `test_crud_base.py`: `TaskCategory`（アプリ固有モデル）を使用 → portal_core 側に `Group` モデル版を新規作成、アプリ側も残す
- `test_i18n.py`: `from main import app` と `_make_session_cookie` を直接参照 → portal_core テスト用アプリに切り替え
- `test_authorization.py`: アプリ固有（Todo visibility）のため残留

**現在の conftest.py フィクスチャ依存:**

```
db_session ──→ test_user
           ──→ client (authenticated, user_id=1)
           ──→ raw_client (unauthenticated)
           ──→ other_user ──→ client_user2 (authenticated, user_id=2)
```

全フィクスチャが `from main import app` に依存 → portal_core 単体テスト不可。

**翻訳ファイル:** gettext 314キー + JSON 203キー。共通/アプリの境界が曖昧なためフェーズ3では分離しない。

### 4.B 設計方針

#### 4.B.1 portal_core テスト用アプリ

portal_core テストは **PortalApp 単体で構築した最小アプリ** を使用。`from main import app` に依存しない。

```python
# portal_core/tests/conftest.py

import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from portal_core.app_factory import PortalApp
from portal_core.config import CoreConfig
from portal_core.core.security import hash_password
from portal_core.database import get_db
from portal_core.models.user import User

# Configuration
config = CoreConfig()
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pre-compute
TEST_PASSWORD = "testpass"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)

# Session cookie signer
_SESSION_SIGNER = TimestampSigner(str(config.SECRET_KEY))


def _make_session_cookie(data: dict) -> str:
    """Create a signed session cookie (same format as Starlette SessionMiddleware)."""
    payload = base64.b64encode(json.dumps(data).encode("utf-8"))
    return _SESSION_SIGNER.sign(payload).decode("utf-8")


@pytest.fixture(scope="session")
def core_app():
    """Build a portal_core-only FastAPI app for testing."""
    portal = PortalApp(config, title="Test Portal Core")
    portal.setup_core()
    return portal.build()


@pytest.fixture()
def db_session():
    """Create a DB session that rolls back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    user = session.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email="default_user@example.com",
            display_name="Default User",
            password_hash=TEST_PASSWORD_HASH,
            role="admin",
        )
        session.add(user)
        session.flush()
    else:
        user.email = "default_user@example.com"
        user.password_hash = TEST_PASSWORD_HASH
        user.role = "admin"
        user.is_active = True
        user.session_version = 1
        session.flush()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db_session):
    return db_session.query(User).filter(User.id == 1).first()


@pytest.fixture()
def client(core_app, db_session):
    """Authenticated test client (user_id=1)."""
    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    core_app.dependency_overrides[get_current_user_id] = lambda: 1
    session_data = {"user_id": 1, "session_version": 1, "locale": "en"}
    with TestClient(core_app, cookies={"session": _make_session_cookie(session_data)}) as c:
        yield c
    core_app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(core_app, db_session):
    """Unauthenticated test client (for auth tests)."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    with TestClient(core_app, cookies={"session": _make_session_cookie({"locale": "en"})}) as c:
        yield c
    core_app.dependency_overrides.clear()


@pytest.fixture()
def other_user(db_session):
    """Create a second user (user_id=2)."""
    user = User(
        id=2,
        email="other_user@example.com",
        display_name="Other User",
        password_hash=TEST_PASSWORD_HASH,
        session_version=1,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def client_user2(core_app, db_session, other_user):
    """Authenticated test client (user_id=2)."""
    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    core_app.dependency_overrides[get_db] = override_get_db
    core_app.dependency_overrides[get_current_user_id] = lambda: 2
    session_data = {"user_id": 2, "session_version": 1, "locale": "en"}
    with TestClient(core_app, cookies={"session": _make_session_cookie(session_data)}) as c:
        yield c
    core_app.dependency_overrides.clear()
```

**設計ポイント:**
- `core_app` は `scope="session"` で1回だけ構築（テスト速度向上）
- `_make_session_cookie()` を portal_core conftest で定義
- 全フィクスチャが `portal_core.*` のみに依存（`app.*` / `main` に依存しない）
- `client` / `raw_client` / `client_user2` は `core_app` に対して DI オーバーライド

#### 4.B.2 アプリ側 conftest.py の更新方針

portal_core conftest とは **独立して定義**。`from main import app`（フルアプリ）を使用。

```python
# tests/conftest.py

import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL, SECRET_KEY
from portal_core.core.security import hash_password
from portal_core.database import get_db
from portal_core.models.user import User
from main import app

# DB setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_PASSWORD = "testpass"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)
_SESSION_SIGNER = TimestampSigner(str(SECRET_KEY))


def _make_session_cookie(data: dict) -> str:
    payload = base64.b64encode(json.dumps(data).encode("utf-8"))
    return _SESSION_SIGNER.sign(payload).decode("utf-8")


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    user = session.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1, email="default_user@example.com", display_name="Default User",
            password_hash=TEST_PASSWORD_HASH, role="admin",
        )
        session.add(user)
        session.flush()
    else:
        user.email = "default_user@example.com"
        user.password_hash = TEST_PASSWORD_HASH
        user.role = "admin"
        user.is_active = True
        user.session_version = 1
        session.flush()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db_session):
    return db_session.query(User).filter(User.id == 1).first()


@pytest.fixture()
def client(db_session):
    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    session_data = {"user_id": 1, "session_version": 1, "locale": "en"}
    with TestClient(app, cookies={"session": _make_session_cookie(session_data)}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, cookies={"session": _make_session_cookie({"locale": "en"})}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def other_user(db_session):
    user = User(
        id=2, email="other_user@example.com", display_name="Other User",
        password_hash=TEST_PASSWORD_HASH, session_version=1,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def client_user2(db_session, other_user):
    from portal_core.core.deps import get_current_user_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: 2
    session_data = {"user_id": 2, "session_version": 1, "locale": "en"}
    with TestClient(app, cookies={"session": _make_session_cookie(session_data)}) as c:
        yield c
    app.dependency_overrides.clear()
```

**変更点（現行 conftest.py からの差分）:**
- `from app.core.security` → `from portal_core.core.security`
- `from app.database` → `from portal_core.database`
- `from app.models.user` → `from portal_core.models.user`
- `from app.core.deps` → `from portal_core.core.deps`
- `from main import app` はそのまま維持

#### 4.B.3 コアテストのインポートパス修正

| 変更前 | 変更後 | 該当数 |
|--------|--------|-------|
| `from app.core.auth.password_policy import ...` | `from portal_core.core.auth.password_policy import ...` | 1 |
| `from app.core.auth.oauth.xxx import ...` | `from portal_core.core.auth.oauth.xxx import ...` | 1 |
| `from app.core.exceptions import ...` | `from portal_core.core.exceptions import ...` | 1 |
| `from app.core.i18n import ...` | `from portal_core.core.i18n import ...` | 1 |
| `from app.models.xxx import ...` | `from portal_core.models.xxx import ...` | 3 |
| `from app.database import get_db` | `from portal_core.database import get_db` | 1 |
| `from main import app` | 削除（`core_app` フィクスチャ使用） | 1 |
| `from tests.conftest import _make_session_cookie` | 削除（conftest で直接定義） | 1 |

#### 4.B.4 翻訳ファイルの方針

**フェーズ3では翻訳ファイルを分離しない。**

暫定措置:
- `test_i18n.py` を portal_core に移動する際、翻訳ファイルのパスをプロジェクトルートの `translations/` を参照するよう設定
- portal_core の conftest で翻訳ディレクトリをプロジェクトルートに向ける

#### 4.B.5 test_crud_base.py の扱い

- portal_core 側: `Group` モデル（コアモデル）を使う新版を作成
- アプリ側: `TaskCategory` 版をそのまま残す

### 4.C 作業一覧

| # | 作業 | 状態 | 詳細 | 影響ファイル |
|---|------|------|------|------------|
| 3-1 | portal_core/tests/ ディレクトリ作成 + conftest.py | ✅ | `core_app` + 6フィクスチャ + `_make_session_cookie` を実装。`attendance_presets` スタブテーブル登録 | `portal_core/tests/conftest.py`, `portal_core/tests/__init__.py` |
| 3-2 | コアテスト8ファイルを portal_core/tests/ に移動 | ✅ | 8ファイル移動 + インポートパス修正。test_auth(10件), test_auth_security(27件), test_oauth(22件), test_password_reset(23件), test_users(28件), test_groups(11件), test_websocket(4件), test_i18n(13件) | 8ファイル |
| 3-3 | portal_core 用 test_crud_base.py 新規作成 | ✅ | `Group` モデル使用（13件）。アプリ側の `TaskCategory` 版も残留 | `portal_core/tests/test_crud_base.py` |
| 3-4 | portal_core 用 pytest 設定 | ✅ | `[tool.pytest.ini_options]` に `testpaths`, `pythonpath` 追加 | `portal_core/pyproject.toml` |
| 3-5 | portal_core 単体テスト実行確認 | ✅ | 151テスト全パス | - |
| 3-6 | アプリ側 conftest.py を更新 | ✅ | インポートパスを `portal_core.*` に変更（`from main import app` は維持） | `tests/conftest.py` |
| 3-7 | アプリ側テストから移動済みファイルを削除 | ✅ | 8ファイル削除 | 8ファイル |
| 3-8 | アプリ側テスト実行確認 | ✅ | 500テスト全パス | - |
| 3-9 | 翻訳ファイルの暫定対応 | ✅ | 対応不要（i18n.py の LOCALE_DIR が `pip install -e` 環境でプロジェクトルートの `translations/` を正しく参照） | - |
| 3-10 | ドキュメント更新 | ✅ | CLAUDE.md, spec_nonfunction.md, spec_common_separation.md 更新 | 3ファイル |
| 3-11 | pip install -e 動作確認 | ✅ | `pip install -e portal_core/` + アプリ起動 + 全テストパス確認 | - |

### 4.D 作業の依存関係

```
3-1 portal_core conftest 作成
  → 3-2 コアテスト移動（3-1 完了後）
  → 3-3 CRUDBase テスト作成（3-1 完了後）
  → 3-4 pytest 設定（3-1 完了後）
    → 3-5 portal_core テスト実行確認（3-2, 3-3, 3-4 完了後）
      → 3-6 アプリ側 conftest 更新（3-5 完了後）
        → 3-7 移動済みファイル削除（3-6 完了後）
          → 3-8 アプリ側テスト実行確認（3-7 完了後）
3-9 翻訳暫定対応（3-2 と並行可能）
3-10 ドキュメント更新（3-8 完了後）
3-11 pip install -e 確認（3-8 完了後）
```

### 4.E リスク評価

| リスク | 確率 | 影響 | 緩和策 |
|--------|------|------|--------|
| portal_core テスト用アプリにコアルーターが不足 | 低 | 高 | `setup_core()` で全コアルーター登録済み |
| conftest のフィクスチャ依存で想定外のエラー | 中 | 中 | 各フィクスチャを段階的にテスト |
| `test_i18n.py` が翻訳ファイルを見つけられない | 高 | 低 | conftest で翻訳ディレクトリを設定 |
| `monkeypatch`/`mock.patch` のターゲットパス不一致 | 中 | 中 | フェーズ2で3ファイル修正済みの経験あり |
| アプリ側テストが portal_core conftest に暗黙依存 | 低 | 高 | 独立して定義（import しない） |

### 4.F 最終ディレクトリ構造（フェーズ3完了後）

```
portal_core/
├── pyproject.toml              # [tool.pytest.ini_options] 追加
├── portal_core/
│   └── (既存のコード)
└── tests/                      # ★ NEW
    ├── __init__.py
    ├── conftest.py             # core_app + 6フィクスチャ
    ├── test_auth.py            # 12 tests
    ├── test_auth_security.py   # 27 tests
    ├── test_oauth.py           # 22 tests
    ├── test_password_reset.py  # 23 tests
    ├── test_users.py           # 28 tests
    ├── test_groups.py          # 11 tests
    ├── test_websocket.py       # 4 tests
    ├── test_i18n.py            # 17 tests
    └── test_crud_base.py       # ~13 tests (Group モデル使用)

tests/                          # アプリ固有テストのみ残る
├── conftest.py                 # portal_core パスに更新済み
├── test_todos.py
├── test_attendances.py
├── test_tasks.py
├── test_task_list.py
├── test_task_categories.py
├── test_reports.py
├── test_summary.py
├── test_presence.py
├── test_logs.py
├── test_log_sources.py
├── test_log_scanner.py
├── test_alerts.py
├── test_alert_rules.py
├── test_calendar.py
├── test_calendar_rooms.py
├── test_authorization.py
├── test_site_links.py
└── test_crud_base.py           # TaskCategory 使用版（残留）
```

**テスト実行コマンド:**

```bash
# portal_core 単体テスト（151テスト）
cd portal_core && pytest tests/ -q

# アプリ固有テスト（500テスト）
pytest tests/ -q

# 全テスト（CI用）
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q
```
