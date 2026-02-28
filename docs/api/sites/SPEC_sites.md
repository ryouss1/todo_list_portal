# サイトリンク機能 設計書

> 本ドキュメントは [spec.md](../../spec.md) の補足資料です。
>
> Webサービスのリンク集をグループ別カードUIで管理し、
> バックグラウンドの死活監視でステータスをリアルタイム表示する機能。

---

## 1. 概要

### 1.1 目的

- 業務で使用する Web サービスの URL を一元管理し、ワンクリックでアクセス可能にする
- 定期的なヘルスチェックで稼働状態をリアルタイム確認
- グループ別カード UI で視認性を向上、URL は非表示で名称のみ表示

### 1.2 主要機能

| 機能 | 説明 |
|------|------|
| リンク管理 | 名称・URL・グループ・説明の登録・編集・削除 |
| グループ管理 | リンクのグループ化（色・アイコン・並び順） |
| 死活監視 | バックグラウンドで HTTP ヘルスチェック（デフォルト 5 分間隔、可変） |
| ステータス表示 | UP / DOWN / TIMEOUT / ERROR / UNKNOWN を色付きドットで表示 |
| リアルタイム更新 | ステータス変化時に WebSocket `/ws/sites` で全クライアントに通知 |
| ワンクリック遷移 | カードクリックでターゲット URL を別タブで開く |
| URL 非表示 | 一覧画面では URL を表示しない。編集モーダルのみで確認可能 |

### 1.3 設計方針

| 方針 | 内容 |
|------|------|
| 登録者 | 全認証ユーザーが自由に登録可能 |
| 編集・削除 | 登録者本人または admin が可能 |
| グループ管理 | admin のみ作成・更新・削除可能 |
| URL 保護 | レスポンスから URL を除外（一覧・詳細 API）。編集専用の URL 取得 API を別途提供 |
| ヘルスチェック | `httpx.AsyncClient` による非同期 HTTP HEAD リクエスト（HEAD 非対応は GET フォールバック） |
| ステータス伝播 | 変化時のみ WebSocket ブロードキャスト（全ポーリング毎にはブロードキャストしない） |

---

## 2. データモデル

### 2.1 ER 図

```
site_groups (1) ──── (N) site_links.group_id  (SET NULL)
users       (1) ──── (N) site_links.created_by (SET NULL)
```

### 2.2 site_groups テーブル

リンクのグループ（カテゴリ）情報を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | グループ ID |
| name | String(100) | NOT NULL, UNIQUE | グループ名 |
| description | String(500) | NULL 許可 | 説明 |
| color | String(7) | NOT NULL, DEFAULT `'#6c757d'` | 表示色（CSS hex 形式: `#RRGGBB`） |
| icon | String(50) | NULL 許可 | Bootstrap Icons クラス名（例: `bi-server`） |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順（昇順） |
| created_at | DateTime(TZ) | server_default `now()` | 作成日時 |

- モデルファイル: `app/models/site_link.py`

### 2.3 site_links テーブル

リンク情報と監視状態を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | リンク ID |
| name | String(200) | NOT NULL | 表示名 |
| url | String(2000) | NOT NULL | URL（DB には平文、API レスポンスには含めない） |
| description | String(500) | NULL 許可 | 説明・メモ |
| group_id | Integer | FK(site_groups.id, SET NULL), NULL 許可, INDEX | グループ ID |
| created_by | Integer | FK(users.id, SET NULL), NOT NULL, INDEX | 登録者 ID |
| sort_order | Integer | NOT NULL, DEFAULT 0 | グループ内表示順 |
| is_enabled | Boolean | NOT NULL, DEFAULT true | リンク有効/無効 |
| check_enabled | Boolean | NOT NULL, DEFAULT true | ヘルスチェック有効/無効 |
| check_interval_sec | Integer | NOT NULL, DEFAULT 300 | チェック間隔（秒、60〜3600） |
| check_timeout_sec | Integer | NOT NULL, DEFAULT 10 | HTTP タイムアウト（秒、3〜60） |
| check_ssl_verify | Boolean | NOT NULL, DEFAULT true | SSL 証明書を検証するか（自己署名証明書サイト用） |
| status | String(20) | NOT NULL, server_default `'unknown'` | 現在のステータス |
| response_time_ms | Integer | NULL 許可 | 最終応答時間（ミリ秒） |
| http_status_code | Integer | NULL 許可 | 最終 HTTP ステータスコード |
| last_checked_at | DateTime(TZ) | NULL 許可 | 最終チェック日時 |
| last_status_changed_at | DateTime(TZ) | NULL 許可 | ステータス変化日時 |
| consecutive_failures | Integer | NOT NULL, DEFAULT 0 | 連続失敗回数 |
| last_error | Text | NULL 許可 | 最終エラーメッセージ（接続エラー等） |
| created_at | DateTime(TZ) | server_default `now()` | 作成日時 |
| updated_at | DateTime(TZ) | server_default `now()`, onupdate | 更新日時 |

- モデルファイル: `app/models/site_link.py`

**status 値:**

| 値 | 条件 | 色 |
|----|------|-----|
| `up` | HTTP 200〜399 で応答 | 🟢 緑 |
| `down` | HTTP 400〜599 で応答 | 🔴 赤 |
| `timeout` | `check_timeout_sec` 超過 | 🟠 橙 |
| `error` | 接続エラー（DNS 失敗・接続拒否等） | 🔴 赤 |
| `unknown` | 未チェック / `check_enabled=false` | ⚪ グレー |

---

## 3. バックグラウンドチェッカー

### 3.1 概要

`app/services/site_checker.py` に実装するバックグラウンドタスク。
`log_scanner.py` と同じパターン（`asyncio.create_task` + `SessionLocal`）で動作する。
`httpx.AsyncClient` を使用した**完全非同期**実装（スレッドプールは不要）。

### 3.2 チェックフロー

```
start_checker(app) — lifespan 起動時
  ↓
_checker_loop() [無限ループ、SITE_CHECKER_LOOP_INTERVAL 秒間隔]
  │
  ├── SessionLocal で DB セッション生成
  ├── is_enabled=true, check_enabled=true のリンクを全件取得
  │
  └── 各リンクについて（並行実行: asyncio.gather）:
       │
       ├── check_interval_sec 経過チェック
       │   └── last_checked_at が None、または経過秒数 >= check_interval_sec の場合のみ実行
       │
       ├── _check_link(link) — HTTP チェック
       │   ├── httpx.AsyncClient(verify=check_ssl_verify, timeout=check_timeout_sec)
       │   ├── HEAD リクエスト送信
       │   ├── HTTP 405 Method Not Allowed → GET リクエストにフォールバック
       │   ├── ステータス判定:
       │   │   ├── 200-399 → "up"
       │   │   ├── 400-599 → "down"
       │   │   ├── httpx.TimeoutException → "timeout"
       │   │   └── その他例外 → "error"
       │   └── CheckResult(status, response_time_ms, http_status_code, error_msg) を返す
       │
       ├── DB 更新（status, response_time_ms, http_status_code,
       │           last_checked_at, consecutive_failures, last_error）
       │
       └── ステータスが前回から変化した場合のみ:
            └── site_ws_manager.broadcast(status_change_dict)
```

**並行実行**: チェック対象リンクを `asyncio.gather(*tasks, return_exceptions=True)` で並行実行し、1 つの失敗が他リンクのチェックを止めないようにする。

### 3.3 設定値（`app/config.py` に追加）

| 環境変数 | デフォルト | 説明 |
|---------|----------|------|
| `SITE_CHECKER_ENABLED` | `false` | バックグラウンドチェッカーの有効/無効 |
| `SITE_CHECKER_LOOP_INTERVAL` | `60` | メインループ間隔（秒） |
| `SITE_CHECK_MAX_REDIRECTS` | `5` | リダイレクト最大数 |

---

## 4. API エンドポイント

### 4.1 サイトリンク API (`/api/sites`)

| メソッド | パス | 認可 | 説明 | ステータスコード |
|---------|------|------|------|----------------|
| GET | `/api/sites/` | 認証ユーザー | リンク一覧取得（URL 除く） | 200 |
| POST | `/api/sites/` | 認証ユーザー | リンク作成 | 201 |
| GET | `/api/sites/{id}` | 認証ユーザー | リンク詳細取得（URL 除く） | 200 / 404 |
| GET | `/api/sites/{id}/url` | 登録者 or Admin | リンクの URL 取得（編集用） | 200 / 403 / 404 |
| PUT | `/api/sites/{id}` | 登録者 or Admin | リンク更新 | 200 / 403 / 404 |
| DELETE | `/api/sites/{id}` | 登録者 or Admin | リンク削除 | 204 / 403 / 404 |
| POST | `/api/sites/{id}/check` | 認証ユーザー | 手動チェック実行 | 200 / 404 |

### 4.2 グループ API (`/api/site-groups`)

| メソッド | パス | 認可 | 説明 | ステータスコード |
|---------|------|------|------|----------------|
| GET | `/api/site-groups/` | 認証ユーザー | グループ一覧取得 | 200 |
| POST | `/api/site-groups/` | Admin のみ | グループ作成 | 201 / 400 |
| PUT | `/api/site-groups/{id}` | Admin のみ | グループ更新 | 200 / 400 / 404 |
| DELETE | `/api/site-groups/{id}` | Admin のみ | グループ削除 | 204 / 404 |

### 4.3 WebSocket

| パス | 認証 | 説明 |
|------|------|------|
| `/ws/sites` | セッション認証 | ステータス変化のリアルタイム通知 |

- 未認証の場合 `code=4401` で close（他 WebSocket と同パターン）

---

## 5. スキーマ定義

### 5.1 SiteGroupCreate

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| name | str | Yes | グループ名（最大100文字） |
| description | str | No | 説明（最大500文字） |
| color | str | No | CSS hex 色（`#RRGGBB` 形式、デフォルト `#6c757d`） |
| icon | str | No | Bootstrap Icons クラス名（例: `bi-server`） |
| sort_order | int | No | 表示順（デフォルト 0） |

### 5.2 SiteGroupResponse

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | グループ ID |
| name | str | グループ名 |
| description | str \| null | 説明 |
| color | str | 表示色 |
| icon | str \| null | アイコン |
| sort_order | int | 表示順 |
| link_count | int | 所属リンク数（未グループはカウントしない） |

### 5.3 SiteLinkCreate

| フィールド | 型 | 必須 | バリデーション |
|-----------|-----|------|-------------|
| name | str | Yes | max 200文字 |
| url | str | Yes | `http://` または `https://` で始まること |
| description | str | No | max 500文字 |
| group_id | int | No | 存在するグループ ID |
| sort_order | int | No | デフォルト 0 |
| is_enabled | bool | No | デフォルト true |
| check_enabled | bool | No | デフォルト true |
| check_interval_sec | int | No | 60〜3600、デフォルト 300 |
| check_timeout_sec | int | No | 3〜60、デフォルト 10 |
| check_ssl_verify | bool | No | デフォルト true |

### 5.4 SiteLinkResponse

`url` フィールドは**含めない**（UI では URL を表示しないため）。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | リンク ID |
| name | str | 表示名 |
| description | str \| null | 説明 |
| group_id | int \| null | グループ ID |
| group_name | str \| null | グループ名（JOIN） |
| created_by | int | 登録者 ID |
| sort_order | int | 表示順 |
| is_enabled | bool | 有効フラグ |
| check_enabled | bool | チェック有効フラグ |
| check_interval_sec | int | チェック間隔（秒） |
| check_timeout_sec | int | タイムアウト（秒） |
| check_ssl_verify | bool | SSL 証明書検証フラグ |
| status | str | 現在ステータス |
| response_time_ms | int \| null | 最終応答時間（ms） |
| http_status_code | int \| null | 最終 HTTP ステータスコード |
| last_checked_at | datetime \| null | 最終チェック日時 |
| last_status_changed_at | datetime \| null | ステータス変化日時 |
| consecutive_failures | int | 連続失敗回数 |
| last_error | str \| null | 最終エラーメッセージ |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

### 5.5 SiteUrlResponse（編集専用）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | リンク ID |
| url | str | URL（平文） |

### 5.6 SiteCheckResponse（手動チェック結果）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | リンク ID |
| status | str | チェック結果 |
| previous_status | str | 前回ステータス |
| response_time_ms | int \| null | 応答時間（ms） |
| http_status_code | int \| null | HTTP ステータスコード |
| checked_at | datetime | チェック実行日時 |
| message | str | 結果メッセージ（例: `"HTTP 200 OK (123ms)"`） |

---

## 6. UI 設計

### 6.1 ページ全体レイアウト (`/sites`)

```
┌─────────────────────────────────────────────────────────────────┐
│  🔗 サイトリンク                 [自動更新 ●] [+ グループ] [+ リンク] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌── ● 業務システム ─────────────────────────────── [+] ──┐      │
│  │                                                         │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │      │
│  │  │ ● UP     │  │ ● UP     │  │ ● DOWN   │              │      │
│  │  │          │  │          │  │          │              │      │
│  │  │ 顧客管理  │  │ 受注管理  │  │ 請求管理  │              │      │
│  │  │          │  │          │  │          │              │      │
│  │  │ 23ms     │  │ 45ms     │  │ ─────    │              │      │
│  │  │ 1分前     │  │ 3分前     │  │ 5分前     │              │      │
│  │  └──────────┘  └──────────┘  └──────────┘              │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                 │
│  ┌── ● 開発ツール ─────────────────────────────── [+] ──┐      │
│  │                                                         │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │      │
│  │  │ ● UP     │  │ ◌ TIMEOUT│  │ ? UNKNOWN│              │      │
│  │  │ GitLab   │  │ Jenkins  │  │ Nexus    │              │      │
│  │  │ 12ms     │  │ ────     │  │ ────     │              │      │
│  │  │ 2分前     │  │ 4分前     │  │ 未確認    │              │      │
│  │  └──────────┘  └──────────┘  └──────────┘              │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                 │
│  ┌── 未分類 ─────────────────────────────────── [+] ──┐       │
│  │  ┌──────────┐                                        │       │
│  │  │ ● UP     │                                        │       │
│  │  │ Wiki     │                                        │       │
│  │  └──────────┘                                        │       │
│  └───────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 リンクカード仕様

各リンクは Bootstrap カード（固定幅 160px）で表示する。

```
┌──────────────────┐
│ ●   ──── [✏][🗑] │  ← ステータスドット + ホバー時に操作ボタン表示
│                  │
│   顧客管理        │  ← リンク名（クリックで別タブ遷移）
│                  │
│   23ms           │  ← 応答時間（up のみ表示）
│   1分前           │  ← 最終チェック時刻（相対表示）
└──────────────────┘
```

**ステータスによる表示変化:**

| ステータス | ドット | カード縁取り | 応答時間 |
|----------|-------|------------|---------|
| `up` | 🟢 緑 | なし | 表示 |
| `down` | 🔴 赤 | 赤（`border-danger`） | 非表示 |
| `timeout` | 🟠 橙 | 橙（`border-warning`） | 非表示 |
| `error` | 🔴 赤 | 赤（`border-danger`） | 非表示 |
| `unknown` | ⚪ グレー | なし | 非表示 |

**ホバー時:**
- カードに影（`shadow-sm`）
- 登録者または admin: 右上に ✏（編集）・🗑（削除）ボタンを表示
- `description` がある場合: Bootstrap Tooltip で表示

**クリック時:**
- `window.open(url, '_blank', 'noopener,noreferrer')` で別タブ遷移
- URL は JS 変数に保持（DOM の `data-*` 属性には含めない — DevTools でのURL漏洩防止）

> **URL の取得方法**: カードクリック時に `GET /api/sites/{id}/url` を呼び出し、レスポンスの URL で遷移。ワンクリックで遷移するため体感遅延は最小限。

### 6.3 グループヘッダー

```
━━━ ● 業務システム ━━━━━━━━━━━━━━━━━━━━━━ [+ リンク追加]
```

- グループカラーのドット（`site_groups.color`）
- グループ名
- `[+ リンク追加]` ボタン（クリックでそのグループを初期選択した追加モーダルを開く）
- admin のみ: グループ名の右に ✏（グループ編集）アイコン

### 6.4 モーダル設計

#### リンク追加・編集モーダル

| フィールド | 種類 | 説明 |
|-----------|------|------|
| 名称 | text | 表示名 |
| URL | url | ターゲット URL（このモーダルのみで表示・編集可） |
| 説明 | textarea | メモ（任意） |
| グループ | select | グループ選択（未分類 = null） |
| 表示順 | number | デフォルト 0 |
| 有効 | checkbox | |
| ヘルスチェック | checkbox | |
| チェック間隔 | number | 秒単位（60〜3600） |
| タイムアウト | number | 秒単位（3〜60） |
| SSL 証明書検証 | checkbox | 自己署名証明書のサイトは OFF |
| 今すぐチェック | button | 編集モーダル内から手動チェックを実行 |

#### グループ追加・編集モーダル（admin のみ）

| フィールド | 種類 | 説明 |
|-----------|------|------|
| グループ名 | text | |
| 説明 | textarea | 任意 |
| 色 | color picker | CSS hex |
| アイコン | text | Bootstrap Icons クラス名（例: `bi-server`） |
| 表示順 | number | |

### 6.5 リアルタイム更新（WebSocket）

WebSocket `/ws/sites` から受信したステータス変化メッセージを受け取ったとき:
1. 対応するカードのドット色を即座に更新
2. 応答時間・最終チェック時刻を更新
3. カード縁取りを更新
4. `down` / `error` へ変化した場合: `showToast()` でデスクトップ通知

---

## 7. フロントエンド

### 7.1 ファイル

| ファイル | 役割 |
|---------|------|
| `templates/sites.html` | ページテンプレート（`base.html` 継承） |
| `static/js/sites.js` | サイトリンク画面の JavaScript |
| `static/css/sites.css` | カードレイアウト等のカスタムスタイル |

### 7.2 JavaScript 関数

| 関数 | 説明 |
|------|------|
| `loadSites()` | `GET /api/sites/` と `GET /api/site-groups/` を並行取得 |
| `renderPage(links, groups)` | グループ別セクションを構築 |
| `renderGroup(group, links)` | グループヘッダー + カードグリッドを生成 |
| `renderCard(link)` | 単一リンクカードの HTML 生成 |
| `openLinkModal(linkId)` | 編集時は `GET /api/sites/{id}/url` で URL を取得してモーダルへセット |
| `saveLink()` | POST（新規）/ PUT（更新） |
| `deleteLink(id)` | 確認ダイアログ後 DELETE |
| `manualCheck(id)` | `POST /api/sites/{id}/check` → カード即時更新 |
| `openGroupModal(groupId)` | グループ追加・編集モーダル |
| `connectWebSocket()` | `/ws/sites` 接続 + 3 秒で自動再接続 |
| `onStatusUpdate(data)` | WebSocket 受信 → 該当カードのドット・縁取り・時刻を更新 |
| `statusDotClass(status)` | status → Bootstrap badge クラス変換 |
| `formatRelativeTime(dt)` | 相対時間表示（「1分前」「3時間前」等） |

### 7.3 WebSocket メッセージ形式

**ステータス変化通知（サーバー → クライアント）:**

```json
{
    "type": "status_update",
    "link_id": 3,
    "name": "請求管理",
    "status": "down",
    "previous_status": "up",
    "response_time_ms": null,
    "http_status_code": 503,
    "checked_at": "2026-02-19T10:30:00+09:00",
    "message": "HTTP 503 Service Unavailable"
}
```

---

## 8. 認可ルール

| 操作 | 権限 | 実装 |
|------|------|------|
| リンク一覧・詳細（URL 除く） | 認証ユーザー | `Depends(get_current_user_id)` |
| リンク URL 取得 | 登録者 or Admin | サービス層で owner チェック → 403 |
| リンク作成 | 認証ユーザー | `Depends(get_current_user_id)`、`created_by=current_user_id` |
| リンク更新・削除 | 登録者 or Admin | サービス層で owner チェック → 403 |
| 手動チェック | 認証ユーザー | `Depends(get_current_user_id)` |
| グループ CUD | Admin のみ | `Depends(require_admin)` |
| WebSocket `/ws/sites` | セッション認証 | `_ws_get_user_id()` + `4401` |

> **owner チェック**: `site_links.created_by == current_user_id` または `user.role == 'admin'`。
> ルーターは薄いラッパー、サービス層で `ForbiddenError` を raise する。

---

## 9. 設定値（`app/config.py` 追加分）

| 環境変数 | デフォルト | 説明 |
|---------|----------|------|
| `SITE_CHECKER_ENABLED` | `false` | バックグラウンドチェッカーの有効/無効 |
| `SITE_CHECKER_LOOP_INTERVAL` | `60` | メインループ間隔（秒） |
| `SITE_CHECK_MAX_REDIRECTS` | `5` | HTTP リダイレクト最大数 |

チェック間隔・タイムアウトはリンクごとに個別設定（`site_links` のカラム）。
グローバルなデフォルト値は DB の `server_default` で管理（config 値は不要）。

---

## 10. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/site_link.py` | `SiteGroup`・`SiteLink` ORM モデル |
| `app/schemas/site_link.py` | Pydantic スキーマ群 |
| `app/crud/site_link.py` | CRUD 操作（グループ・リンク） |
| `app/services/site_link_service.py` | ビジネスロジック（owner チェック・URL 管理） |
| `app/services/site_checker.py` | バックグラウンドチェッカー（httpx.AsyncClient） |
| `app/routers/api_sites.py` | `/api/sites` + `/api/site-groups` API |
| `main.py` | `/ws/sites` WebSocket + lifespan に checker 追加 |
| `templates/sites.html` | ページテンプレート |
| `static/js/sites.js` | フロントエンド JS |
| `static/css/sites.css` | カードスタイル |
| `tests/test_site_links.py` | テスト |
| `alembic/versions/XXXX_add_site_links.py` | マイグレーション |

---

## 11. テスト計画

| テストクラス | 検証内容 | 件数 |
|-------------|---------|------|
| `TestSiteGroupCRUD` | グループ CRUD + 重複名エラー + RBAC（非 admin は 403） | 9件 |
| `TestSiteLinkCRUD` | リンク CRUD + URL バリデーション + グループ FK | 10件 |
| `TestSiteLinkOwner` | 登録者以外は PUT/DELETE で 403、admin は可 | 6件 |
| `TestSiteLinkUrl` | URL 非表示（一覧・詳細に url 含まない）、URL 取得 API の認可 | 5件 |
| `TestSiteLinkCheck` | 手動チェック（httpx モック: 200/503/timeout/error） | 6件 |
| `TestSiteChecker` | ポーリング判定・並行実行・エラー隔離・WebSocket ブロードキャスト | 8件 |
| `TestSitePage` | ページレスポンス・ナビゲーション | 2件 |
| **合計** | | **46件** |

---

## 12. マイグレーション

| 項目 | 内容 |
|------|------|
| 新規リビジョン | `<new_revision>` (`add_site_links`) |
| 依存リビジョン | `6ddf43a20423` (`add_unique_constraint_attendances_user_date`) |
| 作成テーブル | `site_groups`（7 カラム）、`site_links`（22 カラム） |

---

## 13. 技術的負債・制限事項

| 項目 | 内容 |
|------|------|
| URL 平文保存 | `site_links.url` は暗号化なし。DB アクセス可能な攻撃者には URL が露出する（ログソースの認証情報とは異なる判断: URL はリンク集の本質的情報のため暗号化より利便性を優先） |
| HTTP 認証 | Basic Auth・Form 認証が必要なサイトはヘルスチェックが正確でない（認証エラー = `down` と判定される） |
| クリック遅延 | URL 取得のため `GET /api/sites/{id}/url` を経由するため、クリック後にわずかな遅延が発生する。許容できない場合はプリフェッチの検討が必要 |
| 通知機能 | DOWN 検知時のメール・Slack 通知は未実装（アラートルールと連携することで代替可能: ログ経由でアラート生成） |
| アクセス制御 | IP 制限 等のアクセス制限付きサイトはチェックサーバーが対象外のため DOWN と判定される |
| 検索・絞り込み | リンク数が増えた場合の検索・ステータスフィルタ機能は未実装 |
