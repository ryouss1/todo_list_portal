# 設定項目一覧（Setting Reference）

> `app/config.py` で管理する環境変数ベースの設定と、コード内にハードコーディングされている設定値の棚卸し。
> 優先度: **A**（設定ファイル化必須） > **B**（設定ファイル化推奨） > **C**（現状維持でも可）

---

## 0. 設定読み込みの仕組み

`app/config.py` は `python-dotenv` を使用し、プロジェクトルートの **`.env`** ファイルから環境変数を自動読み込みします。

```python
from dotenv import load_dotenv
load_dotenv()
```

- `.env` ファイルは `.gitignore` に登録済み（Git管理外）
- **機密情報**（`DATABASE_URL`, `SECRET_KEY`, `DEFAULT_PASSWORD`, `SMTP_PASSWORD` 等）はコード内にデフォルト値を持たないため、`.env` での設定が**必須**です
- パスワード・接続情報を確認する際は **`.env` ファイル**を参照してください

### `.env` ファイルの例

```bash
# Database
DATABASE_URL=postgresql://postgres:<パスワード>@postgres-11-test/todo_list_portal

# Security
SECRET_KEY=<セッション署名キー>
DEFAULT_PASSWORD=<初期ユーザーパスワード>

# SMTP Settings
SMTP_HOST=<SMTPホスト>
SMTP_USERNAME=<SMTPユーザー名>
SMTP_PASSWORD=<SMTPパスワード>
SMTP_FROM_ADDRESS=<送信元アドレス>
```

---

## 1. 既存設定（`app/config.py` に定義済み）

> **注**: `(*)` マークの項目はデフォルト値が空文字列のため、`.env` での設定が必須です。

| 環境変数 | 型 | デフォルト値 | 用途 |
|---------|-----|-------------|------|
| `DATABASE_URL` (*) | str | `""` | PostgreSQL 接続文字列 |
| `DEFAULT_USER_ID` | int | `1` | 初期ユーザーの ID |
| `DEFAULT_EMAIL` | str | `admin@example.com` | 初期ユーザーのメールアドレス |
| `DEFAULT_DISPLAY_NAME` | str | `Default User` | 初期ユーザーの表示名 |
| `SECRET_KEY` (*) | str | `""` | セッション Cookie 署名鍵 |
| `DEFAULT_PASSWORD` (*) | str | `""` | 初期ユーザーのパスワード |
| `LOG_COLLECTOR_ENABLED` | bool | `false` | ログファイル収集バックグラウンドタスクの有効化 |
| `LOG_COLLECTOR_LOOP_INTERVAL` | int | `5` | ログ収集メインループ間隔（秒） |
| `LOG_ALLOWED_PATHS` | str | `""` | ログソースの file_path 許可ディレクトリ（カンマ区切り、空=全許可） |
| `BACKLOG_SPACE` | str | `ottsystems` | Backlog チケット URL 生成用スペース名 |
| `LOG_LEVEL` | str | `INFO` | ログ出力レベル（`logging_config.py` で参照） |
| `LOG_FILE` | str | `app.log` | ログファイル出力先パス（`logging_config.py` で参照） |
| `SMTP_HOST` (*) | str | `""` | SMTPサーバーホスト |
| `SMTP_PORT` | int | `587` | SMTPサーバーポート |
| `SMTP_USERNAME` (*) | str | `""` | SMTP認証ユーザー名 |
| `SMTP_PASSWORD` (*) | str | `""` | SMTP認証パスワード |
| `SMTP_FROM_ADDRESS` | str | `noreply@example.com` | メール送信元アドレス |
| `SMTP_USE_TLS` | bool | `true` | STARTTLS使用フラグ |
| `SMTP_USE_SSL` | bool | `false` | SSL/TLS使用フラグ |

---

## 2. サーバー設定 [優先度 A]

> `main.py:176` の `uvicorn.run()` にハードコーディング。

| 環境変数（案） | 現在のハードコード値 | ファイル:行 | 用途 |
|---------------|-------------------|-----------|------|
| `SERVER_HOST` | `"0.0.0.0"` | `main.py:176` | サーバーバインドアドレス |
| `SERVER_PORT` | `8000` | `main.py:176` | サーバーポート番号 |
| `SERVER_RELOAD` | `True` | `main.py:176` | ホットリロード（本番では `false` にすべき） |

---

## 3. セッション・Cookie 設定 [優先度 A]

> `main.py:95` の `SessionMiddleware` にデフォルト値を暗黙使用。

| 環境変数（案） | 現在のデフォルト値 | ファイル:行 | 用途 |
|---------------|-----------------|-----------|------|
| `SESSION_MAX_AGE` | `1209600`（14日、Starlette デフォルト） | `main.py:95` | セッション有効期限（秒） |
| `SESSION_COOKIE_SECURE` | `False`（Starlette デフォルト） | `main.py:95` | HTTPS 専用 Cookie（本番では `true`） |
| `SESSION_COOKIE_SAMESITE` | `"lax"` | `main.py:95` | SameSite 属性 |
| `SESSION_COOKIE_HTTPONLY` | `True` | `main.py:95` | HttpOnly フラグ |

---

## 4. データベース接続プール設定 [優先度 B]

> `app/database.py:6` の `create_engine()` で未設定。SQLAlchemy デフォルト値が使用される。

| 環境変数（案） | 現在のデフォルト値 | ファイル:行 | 用途 |
|---------------|-----------------|-----------|------|
| `DB_POOL_SIZE` | `5`（SQLAlchemy デフォルト） | `app/database.py:6` | コネクションプール基本サイズ |
| `DB_MAX_OVERFLOW` | `10`（SQLAlchemy デフォルト） | `app/database.py:6` | プールの最大追加接続数 |
| `DB_POOL_RECYCLE` | `-1`（無制限、SQLAlchemy デフォルト） | `app/database.py:6` | 接続再利用の最大秒数（PostgreSQL のタイムアウト対策） |
| `DB_POOL_PRE_PING` | `True` | `app/database.py:6` | 接続前ヘルスチェック（現在ハードコード） |

---

## 5. ログローテーション設定 [優先度 B]

> `app/core/logging_config.py:24-26` にハードコーディング。

| 環境変数（案） | 現在のハードコード値 | ファイル:行 | 用途 |
|---------------|-------------------|-----------|------|
| `LOG_MAX_BYTES` | `10485760`（10 MB） | `logging_config.py:24` | ログファイルの最大サイズ |
| `LOG_BACKUP_COUNT` | `5` | `logging_config.py:25` | バックアップログファイルの保持数 |

---

## 6. ビジネスロジック定数 [優先度 B]

| 環境変数（案） | 現在のハードコード値 | ファイル:行 | 用途 |
|---------------|-------------------|-----------|------|
| `MAX_ATTENDANCE_BREAKS` | `3` | `app/services/attendance_service.py:18` | 1日の最大休憩回数 |
| `DEFAULT_TASK_CATEGORY_ID` | `7` | `app/services/task_service.py:20` | タスク完了時の自動日報カテゴリ（「その他」） |

---

## 7. API デフォルトリミット [優先度 B]

> 全一覧エンドポイントの取得件数上限。

| 環境変数（案） | 現在のハードコード値 | ファイル:行 | 用途 |
|---------------|-------------------|-----------|------|
| `API_LOG_LIMIT` | `100` | `app/routers/api_logs.py:22,31` | ログ一覧の既定取得件数 |
| `API_ALERT_LIMIT` | `100` | `app/routers/api_alerts.py:17` | アラート一覧の既定取得件数 |
| `API_PRESENCE_LOG_LIMIT` | `50` | `app/crud/presence.py:37` | プレゼンスログの既定取得件数 |

---

## 8. ログソース収集設定 [優先度 B]

| 環境変数（案） | 現在のハードコード値 | ファイル:行 | 用途 |
|---------------|-------------------|-----------|------|
| `LOG_SOURCE_DEFAULT_POLLING_SEC` | `30` | `app/schemas/log_source.py:36` | 新規ログソースのデフォルトポーリング間隔（秒） |
| `LOG_SOURCE_MIN_POLLING_SEC` | `5` | `app/schemas/log_source.py:57` | ポーリング間隔の最小値（秒） |

---

## 9. フロントエンド設定 [優先度 B]

### 9.1 CDN URL

> `templates/base.html` と `templates/login.html` の2箇所で重複定義。

| 環境変数（案） | 現在のハードコード値 | ファイル | 用途 |
|---------------|-------------------|---------|------|
| `BOOTSTRAP_CSS_URL` | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css` | `base.html:7`, `login.html:7` | Bootstrap CSS CDN |
| `BOOTSTRAP_ICONS_URL` | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css` | `base.html:8`, `login.html:8` | Bootstrap Icons CDN |
| `BOOTSTRAP_JS_URL` | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js` | `base.html:139` | Bootstrap JS CDN |

### 9.2 JavaScript 定数

> JS 側は `window.__xxx` グローバル変数でテンプレートから注入するパターンを使用。

| 変数名 | 現在のハードコード値 | ファイル:行 | 用途 |
|--------|-------------------|-----------|------|
| `window.__backlogSpace` | `"ottsystems"`（フォールバック） | `tasks.js`, `presence.js` | Backlog チケット URL 用スペース名 |
| — (未対応) | `"ottsystems"` **直接ハードコード** | `task_list.js:260` | 同上（`window.__backlogSpace` 未使用 = **ISSUE-056**） |

### 9.3 Toast / WebSocket

| 項目 | 現在のハードコード値 | ファイル:行 | 用途 |
|------|-------------------|-----------|------|
| Toast 表示時間 | `4000` ms | `common.js:42` | 通知トーストの自動非表示時間 |
| WebSocket 再接続間隔 | `3000` ms | `logs.js:54`, `presence.js:84`, `alerts.js:212` | WebSocket 切断後の再接続待機時間 |

---

## 10. シードデータ [優先度 C]

> `app/init_db.py` にハードコーディング。DB に初回のみ投入される。

### 10.1 勤怠プリセット（`seed_default_presets()`）

| ID | 名前 | 出勤 | 退勤 | 休憩開始 | 休憩終了 |
|----|------|------|------|---------|---------|
| 1 | 9:00-18:00 | 09:00 | 18:00 | 12:00 | 13:00 |
| 2 | 8:30-17:30 | 08:30 | 17:30 | 12:00 | 13:00 |

### 10.2 タスクカテゴリ（`seed_default_categories()`）

| ID | 名前 |
|----|------|
| 7 | その他 |
| 8 | OWVIS(ライト) |
| 9 | OWVIS(旧式) |
| 10 | OPAS(新規開発) |
| 11 | OPAS(追加開発) |
| 12 | OPAS(運用保守) |
| 13 | OPTAS |
| 14 | 指定伝票 |
| 15 | 物流統合PJ |
| 16 | システム(その他) |
| 17 | インフラ |
| 18 | 情シス |
| 19 | 社内業務(シス) |
| 20 | 社内業務(ロジ) |
| 21 | 社内業務(BP) |
| 22 | 集荷管理システム |

**備考**: シードデータは初回起動時のみ DB に投入される。以降はアプリケーション（API）から管理する想定のため、設定ファイル化の必要性は低い。

---

## 11. セキュリティ固定値 [優先度 C]

> 変更の必要性が低い、またはコード内に留めるべき定数。

| 項目 | 値 | ファイル:行 | 備考 |
|------|-----|-----------|------|
| WebSocket 認証失敗コード | `4401` | `main.py:129,145,161` | カスタム close code |
| 公開パスプレフィックス | `"/login", "/static/", "/api/auth/", "/ws/"` | `main.py:82` | auth_middleware バイパス対象 |
| CSRF チェック対象メソッド | `"POST", "PUT", "PATCH", "DELETE"` | `main.py:59` | 状態変更リクエスト |
| パスワードハッシュ | passlib + bcrypt | `app/core/security.py` | ハッシュアルゴリズム |
| ユーザーロール種別 | `"admin"`, `"user"` | `app/models/user.py` | RBAC ロール定義 |

---

## まとめ

### 優先度別アクション

| 優先度 | 件数 | 内容 |
|--------|------|------|
| **A（必須）** | 7項目 | サーバー設定（3）、セッション設定（4） — 本番運用で必須 |
| **B（推奨）** | 17項目 | DB プール（4）、ログローテーション（2）、ビジネス定数（2）、API リミット（3）、ログソース設定（2）、CDN URL（3）、JS 定数（1=ISSUE-056 修正含む） |
| **C（現状維持可）** | 11項目 | シードデータ（マスタ）、セキュリティ固定値 |
| **合計** | **35項目** | |

### 設定ファイル化の実装方針

1. **`app/config.py`** — `python-dotenv` + `os.environ.get()` で `.env` ファイルから読み込み（実装済み）
2. **`.env`** ファイル — 機密情報はここに集約（`.gitignore` 登録済み）
3. **`main.py`** の `uvicorn.run()` / `SessionMiddleware` で config 値を参照
4. **`app/database.py`** の `create_engine()` にプール設定を追加
5. **テンプレート**: `templates.env.globals` 経由で CDN URL 等をテンプレートに注入（既存の `backlog_space` パターンを踏襲）
6. **JS 定数**: `window.__xxx` パターンで `base.html` からテンプレート変数を注入
