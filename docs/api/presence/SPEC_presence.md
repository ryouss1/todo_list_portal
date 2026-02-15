# Presence 機能仕様書

> リアルタイムプレゼンス（在席状況）管理機能の完全な仕様。ステータス更新・WebSocket リアルタイム配信・アクティブチケット表示を含む。

---

## 1. 概要

### 1.1 背景

チームメンバーの在席状況をリアルタイムに共有し、誰がどの状態で何の作業をしているかを一覧で把握できる機能。
WebSocket を使ったリアルタイム通知により、ステータス変更が即座に全ユーザーに反映される。

### 1.2 目的

- 各ユーザーの在席ステータス（available / away / out / break / offline / meeting / remote）を管理
- ステータス変更を WebSocket でリアルタイム配信
- 作業中タスクの Backlog チケット ID をプレゼンス画面に表示
- ステータス変更履歴の記録・参照

### 1.3 基本フロー

```
ユーザー → [ステータス更新] → PresenceStatus (upsert) + PresenceLog (append)
                                    ↓
                             WebSocket broadcast → 全接続クライアントに即時反映
                                    ↓
                             Presence 画面の All Users テーブルが自動更新
```

- ステータスは 1 ユーザー 1 レコード（UNIQUE 制約）で upsert
- 変更の都度 PresenceLog に履歴を append（監査証跡）
- Tasks 画面で `in_progress` かつ `backlog_ticket_id` が設定されたタスクは、プレゼンス一覧にチケットリンクとして表示される

---

## 2. データモデル

### 2.1 presence_statuses テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | ステータスID |
| user_id | INTEGER | FK → users.id, NOT NULL, UNIQUE | ユーザーID（1 ユーザー 1 レコード） |
| status | VARCHAR(20) | NOT NULL, DEFAULT "offline" | 現在のステータス |
| message | TEXT | NULL 可 | ステータスメッセージ（任意） |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 最終更新日時 |

### 2.2 presence_logs テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | ログID |
| user_id | INTEGER | FK → users.id, NOT NULL | ユーザーID |
| status | VARCHAR(20) | NOT NULL | 変更後のステータス |
| message | TEXT | NULL 可 | 変更時のメッセージ |
| changed_at | DATETIME(TZ) | server_default=now() | 変更日時 |

### 2.3 tasks テーブルとの連携（アクティブチケット）

プレゼンス一覧表示時に以下の条件でタスクを取得し、ユーザーごとのアクティブチケットとして表示する。

```
Task.status == "in_progress" AND Task.backlog_ticket_id IS NOT NULL
```

- 条件を満たすタスクは `ActiveTicket` として `PresenceStatusWithUser.active_tickets` に含まれる
- `pending` のタスクや `backlog_ticket_id` が未設定のタスクは対象外

---

## 3. ステータス種別

| ステータス | 表示名 | バッジ色 | CSS クラス | 説明 |
|-----------|--------|---------|-----------|------|
| `available` | Available | 緑 (`#198754`) | `.presence-available` | 在席・対応可能 |
| `away` | Away | 黄 (`#ffc107`, 文字黒) | `.presence-away` | 離席中 |
| `out` | Out | 青 (`#0d6efd`) | `.presence-out` | 外出中 |
| `break` | Break | オレンジ (`#fd7e14`) | `.presence-break` | 休憩中 |
| `offline` | Offline | グレー (`#6c757d`) | `.presence-offline` | オフライン（デフォルト） |
| `meeting` | Meeting | 紫 (`#6f42c1`) | `.presence-meeting` | 会議中 |
| `remote` | Remote | ティール (`#20c997`) | `.presence-remote` | リモート勤務中 |

- スキーマでは `Literal["available", "away", "out", "break", "offline", "meeting", "remote"]` で制約
- 不正なステータス値は `422 Validation Error` で拒否
- ステータス未設定のユーザーは `"offline"` として表示

---

## 4. API エンドポイント

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）

### 4.1 ステータス操作

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| PUT | `/api/presence/status` | 自分のステータスを更新 | `200` PresenceStatusResponse |
| GET | `/api/presence/me` | 自分の現在ステータスを取得 | `200` PresenceStatusResponse |
| GET | `/api/presence/statuses` | 全ユーザーのステータス一覧 | `200` PresenceStatusWithUser[] |
| GET | `/api/presence/logs` | 自分のステータス変更履歴 | `200` PresenceLogResponse[] |

### 4.2 PUT /api/presence/status の処理フロー

1. リクエストボディのバリデーション（`PresenceUpdateRequest`）
2. `presence_statuses` テーブルに upsert（既存なら更新、新規なら作成）
3. `presence_logs` テーブルに履歴レコードを append
4. WebSocket で全接続クライアントにブロードキャスト
5. 更新後の `PresenceStatusResponse` を返却

### 4.3 GET /api/presence/statuses の処理フロー

1. `presence_statuses` テーブルから全ステータスを取得
2. `users` テーブルから全ユーザーを取得
3. `tasks` テーブルから `in_progress` かつ `backlog_ticket_id IS NOT NULL` のタスクを取得
4. ユーザーごとにステータス + 表示名 + アクティブチケットを結合
5. ステータス未設定のユーザーは `"offline"` として含める

### 4.4 GET /api/presence/logs

- 自分のステータス変更履歴のみ取得（他ユーザーの履歴は取得不可）
- 最大 50 件、`changed_at DESC` でソート

---

## 5. WebSocket

### 5.1 エンドポイント

| パス | 認証 | 説明 |
|------|------|------|
| `/ws/presence` | セッション Cookie 必須 | プレゼンス更新のリアルタイム配信 |

### 5.2 接続フロー

```
クライアント → WebSocket 接続要求 (/ws/presence)
    ↓
サーバー: accept() → セッション Cookie 確認
    ↓
認証失敗 → close(code=4401, reason="Not authenticated")
認証成功 → 接続維持（receive_text ループ）
    ↓
クライアント切断 → disconnect() で接続リストから削除
```

### 5.3 ブロードキャストメッセージ

ステータス更新時に全接続クライアントに送信されるメッセージ:

```json
{
  "type": "presence_update",
  "user_id": 1,
  "status": "available",
  "message": "Working on feature X"
}
```

### 5.4 WebSocketManager

`app/services/websocket_manager.py` で定義。`presence_ws_manager` インスタンスを使用。

| メソッド | 説明 |
|---------|------|
| `connect(websocket)` | 接続を受け入れ、`active_connections` リストに追加 |
| `disconnect(websocket)` | 接続をリストから削除 |
| `broadcast(data)` | 全接続にJSON送信。送信失敗の接続は自動削除（dead connection cleanup） |

- `log_ws_manager`, `presence_ws_manager`, `alert_ws_manager` の 3 インスタンスが同一クラスから生成
- ブロードキャスト時に切断済みの接続は自動除去される

### 5.5 クライアント側の WebSocket 処理

```
接続確立 → ws-badge を "Connected" (緑) に更新
    ↓
メッセージ受信: type === "presence_update" → loadPresence() で画面全体を再読み込み
    ↓
接続切断 → ws-badge を "Disconnected" (グレー) に更新 → 3 秒後に自動再接続
```

---

## 6. スキーマ

### PresenceUpdateRequest
```json
{
  "status": "available | away | out | break | offline | meeting | remote (必須)",
  "message": "string (任意)"
}
```

### PresenceStatusResponse
```json
{
  "id": 1,
  "user_id": 1,
  "status": "available",
  "message": "string|null",
  "updated_at": "datetime|null"
}
```

### PresenceStatusWithUser
```json
{
  "user_id": 1,
  "display_name": "Default User",
  "status": "available",
  "message": "string|null",
  "updated_at": "datetime|null",
  "active_tickets": [
    {
      "task_id": 5,
      "task_title": "Feature implementation",
      "backlog_ticket_id": "WHT-123"
    }
  ]
}
```

### ActiveTicket
```json
{
  "task_id": 5,
  "task_title": "string",
  "backlog_ticket_id": "string"
}
```

### PresenceLogResponse
```json
{
  "id": 1,
  "user_id": 1,
  "status": "available",
  "message": "string|null",
  "changed_at": "datetime|null"
}
```

---

## 7. フロントエンド

### 7.1 画面構成（`/presence`）

- テンプレート: `templates/presence.html`
- JavaScript: `static/js/presence.js?v=3`
- ナビバー: `bi-people` アイコンで表示

```
Presence Status ページ
├── 左カラム (col-lg-4)
│   ├── My Status カード
│   │   ├── WebSocket 接続バッジ (Connected / Disconnected)
│   │   ├── Status ドロップダウン（7 種）
│   │   ├── Message テキスト入力
│   │   └── Update Status ボタン
│   └── My History カード
│       └── 直近 10 件のステータス変更履歴
└── 右カラム (col-lg-8)
    └── All Users テーブル
        └── User / Status / Message / Tickets / Updated 列
```

### 7.2 All Users テーブル

| 列 | 説明 |
|------|------|
| User | `display_name`（`escapeHtml` でサニタイズ） |
| Status | ステータスバッジ（CSS クラス `presence-{status}` で色分け） |
| Message | ステータスメッセージ（未設定時は `-`） |
| Tickets | アクティブチケットのリンクバッジ（`bi-link-45deg` アイコン付き） |
| Updated | `updated_at` を `toLocaleString()` で表示 |

### 7.3 アクティブチケット表示

- `in_progress` かつ `backlog_ticket_id` が設定されたタスクを Backlog リンクとして表示
- URL: `https://{BACKLOG_SPACE}.backlog.com/view/{backlog_ticket_id}`
- デフォルト: `https://ottsystems.backlog.com/view/{ticket}`
- `<a>` タグで `target="_blank"` のリンクバッジ（`badge bg-info`）
- 複数チケットは `flex-wrap gap-1` で並列表示

### 7.4 My History

- `GET /api/presence/logs` で自分の履歴を取得（API は最大 50 件返却）
- フロント側で先頭 10 件のみ表示（`logs.slice(0, 10)`）
- 各エントリ: ステータスバッジ + メッセージ + 日時

### 7.5 初期化・データ読み込み

```javascript
// 並列で 3 API を呼び出し
const [myStatus, allStatuses, logs] = await Promise.all([
    api.get('/api/presence/me'),
    api.get('/api/presence/statuses'),
    api.get('/api/presence/logs')
]);
```

- ページ読み込み時に `loadPresence()` + `connectWebSocket()` を実行
- `updateMyStatus()`: PUT 送信後に `loadPresence()` で画面全体を再読み込み
- WebSocket メッセージ受信時にも `loadPresence()` を呼び出し

---

## 8. ビジネスルール

### 8.1 ステータス更新

| ルール | 説明 |
|--------|------|
| 自分のみ更新可能 | 他ユーザーのステータスは変更不可 |
| upsert 方式 | 初回は INSERT、2 回目以降は UPDATE（UNIQUE 制約で 1 ユーザー 1 レコード） |
| 履歴自動記録 | ステータス更新の都度 `presence_logs` に履歴を追加 |
| リアルタイム配信 | 更新後に WebSocket で全接続クライアントに即時ブロードキャスト |
| デフォルトステータス | ステータス未設定のユーザーは `"offline"` として扱う |

### 8.2 可視性

| ルール | 説明 |
|--------|------|
| 全ユーザー公開 | 全認証ユーザーが全ユーザーのステータスを閲覧可能 |
| 履歴は自分のみ | `GET /api/presence/logs` は自分の履歴のみ返却 |
| アクティブチケット | 全ユーザーの `in_progress` タスクのチケットが一覧に表示される |

### 8.3 バリデーション

| ルール | 説明 |
|--------|------|
| ステータス制約 | 7 種のみ許可（`Literal` 型で制約）。不正値は `422` |
| メッセージ任意 | `message` は `null` または文字列。長さ制限なし（TEXT 型） |

### 8.4 WebSocket 認証

| ルール | 説明 |
|--------|------|
| セッション必須 | WebSocket 接続時にセッション Cookie から `user_id` を確認 |
| 未認証時切断 | `code=4401` で即座に切断 |
| 自動再接続 | クライアント側で切断検知後 3 秒で再接続を試行 |

---

## 9. ファイル構成

### 9.1 新規作成（7 ファイル）

| ファイル | 内容 |
|---------|------|
| `app/models/presence.py` | PresenceStatus + PresenceLog モデル |
| `app/schemas/presence.py` | リクエスト/レスポンススキーマ + ActiveTicket |
| `app/crud/presence.py` | CRUD 操作（upsert, log 作成, 一覧取得） |
| `app/services/presence_service.py` | ビジネスロジック（ステータス更新・一覧・チケット結合） |
| `app/routers/api_presence.py` | API エンドポイント（4 ルート） |
| `templates/presence.html` | 画面テンプレート |
| `static/js/presence.js` | フロントエンド JS（WebSocket 接続含む） |

### 9.2 変更（4 ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `app/services/websocket_manager.py` | `presence_ws_manager` インスタンス追加 |
| `main.py` | `/ws/presence` WebSocket エンドポイント + router 登録 |
| `app/routers/pages.py` | `/presence` ページルート追加 |
| `templates/base.html` | Presence ナビリンク追加 |

### 9.3 スタイル

| ファイル | 内容 |
|---------|------|
| `static/css/style.css` | `.presence-{status}` CSS クラス（7 種のバッジ色定義） |

---

## 10. テスト

`tests/test_presence.py` に 15 テストケース（`TestPresenceAPI` クラス）。

### ステータス基本テスト（5 件）
- デフォルトステータスが `"offline"` であることの確認
- ステータス更新（`available`）の確認
- メッセージ付きステータス更新（`away` + "Lunch break"）の確認
- 不正なステータス値の拒否（`422`）の確認
- 複数回更新で最新値が反映されることの確認（upsert 冪等性）

### ステータス種別テスト（2 件）
- `meeting` ステータスの更新確認
- `remote` ステータスの更新確認

### 一覧テスト（2 件）
- 全ステータス一覧の取得確認（リスト形式）
- `display_name` が一覧に含まれることの確認

### 履歴テスト（1 件）
- ステータス変更で `presence_logs` に履歴が作成されることの確認

### 認可テスト（1 件）
- 全ユーザーが全ユーザーのステータスを閲覧できることの確認（cross-user）

### アクティブチケットテスト（4 件）
- `in_progress` + `backlog_ticket_id` 設定済タスクがチケットとして表示されることの確認
- `pending` タスクのチケットが除外されることの確認
- `backlog_ticket_id` 未設定の `in_progress` タスクが除外されることの確認
- 複数アクティブチケットの表示確認

---

## 11. ダッシュボード連携

`templates/index.html` のダッシュボードに Presence サマリーが表示される。

- `GET /api/presence/statuses` を取得
- `"offline"` 以外のユーザー数をカウントし `"{count} / {total} online"` 形式で表示

---

## 12. マイグレーション

- Revision: `29148e04951a`（`86da56d0b359` の次）
- `presence_statuses` テーブル作成（UNIQUE 制約 on `user_id`、DEFAULT `"offline"`）
- `presence_logs` テーブル作成（FK → `users.id`）
