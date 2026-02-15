# Alerts API 仕様書

> 本ドキュメントは [SPEC_API.md](../../SPEC_API.md) の補足資料です。

## 1. 概要

アラートは、システムの異常やイベントを管理するための通知機能である。
アラートは以下の2つの経路で生成される:

1. **手動作成**: 認証済みユーザーが `POST /api/alerts/` で作成
2. **自動生成**: ログ登録時にアラートルールの条件に一致した場合に自動作成（詳細は [SPEC_alert-rules.md](../alert-rules/SPEC_alert-rules.md) を参照）

生成されたアラートは WebSocket (`/ws/alerts`) 経由で全クライアントにリアルタイム通知され、ナビバーの未確認バッジが自動更新される。

### 1.1 機能一覧

| 機能 | 説明 |
|------|------|
| アラート一覧取得 | 全アラートまたはアクティブのみを一覧取得 |
| 未確認件数取得 | 未確認かつアクティブなアラートの件数を取得（ナビバッジ用） |
| 手動アラート作成 | タイトル、メッセージ、重要度を指定してアラートを作成 |
| アラート取得 | ID指定でアラートの詳細を取得 |
| アラート確認 | アラートを確認済みにマーク（確認者・日時を記録） |
| アラート非活性化 | アラートを非アクティブに変更 |
| アラート削除 | アラートを物理削除（admin のみ） |
| リアルタイム通知 | WebSocket で新着アラートを全クライアントに配信 |
| ナビバッジ | 未確認アラート件数をナビバーにバッジ表示 |

### 1.2 認可ルール

| 操作 | 権限 |
|------|------|
| 一覧取得 (`GET /`) | 認証済みユーザー |
| 未確認件数 (`GET /count`) | 認証済みユーザー |
| 手動作成 (`POST /`) | 認証済みユーザー |
| 個別取得 (`GET /{id}`) | 認証済みユーザー |
| 確認 (`PATCH /{id}/acknowledge`) | 認証済みユーザー（確認者として記録） |
| 非活性化 (`PATCH /{id}/deactivate`) | 認証済みユーザー |
| 削除 (`DELETE /{id}`) | admin のみ |

---

## 2. エンドポイント一覧

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/alerts/` | アラート一覧 | 200 | 必要 |
| GET | `/api/alerts/count` | 未確認アラート件数 | 200 | 必要 |
| POST | `/api/alerts/` | 手動アラート作成 | 201 / 422 | 必要 |
| GET | `/api/alerts/{id}` | アラート取得 | 200 / 404 | 必要 |
| PATCH | `/api/alerts/{id}/acknowledge` | アラート確認 | 200 / 404 | 必要 |
| PATCH | `/api/alerts/{id}/deactivate` | アラート非活性化 | 200 / 404 | 必要 |
| DELETE | `/api/alerts/{id}` | アラート削除 | 204 / 404 | 必要（admin） |

---

## 3. エンドポイント詳細

### 3.1 GET /api/alerts/

アラート一覧を作成日時降順で取得する。

- **権限**: 認証済みユーザー
- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| active_only | boolean | false | `true` の場合、`is_active=true` のアラートのみ取得 |
| limit | integer | 100 | 取得件数上限（`API_ALERT_LIMIT` 環境変数で変更可能） |

- **レスポンス**: `200 OK` - `AlertResponse[]`

**レスポンス例:**

```json
[
  {
    "id": 1,
    "title": "ERROR in prod-server",
    "message": "Database connection failed",
    "severity": "critical",
    "source": "prod-server",
    "rule_id": 1,
    "is_active": true,
    "acknowledged": false,
    "acknowledged_by": null,
    "acknowledged_at": null,
    "created_at": "2026-02-12T10:30:00+09:00"
  },
  {
    "id": 2,
    "title": "Manual Alert",
    "message": "Deploy scheduled",
    "severity": "info",
    "source": null,
    "rule_id": null,
    "is_active": true,
    "acknowledged": true,
    "acknowledged_by": 1,
    "acknowledged_at": "2026-02-12T11:00:00+09:00",
    "created_at": "2026-02-12T10:00:00+09:00"
  }
]
```

### 3.2 GET /api/alerts/count

未確認かつアクティブなアラートの件数を取得する。ナビバーのバッジ更新に使用される。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `AlertCountResponse`

**レスポンス例:**

```json
{
  "count": 3
}
```

**カウント条件**: `acknowledged=false` AND `is_active=true`

### 3.3 POST /api/alerts/

手動でアラートを作成する。作成後、WebSocket 経由で全クライアントに通知される。

- **権限**: 認証済みユーザー
- **リクエストボディ**: `AlertCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | アラートタイトル |
| message | string | Yes | - | アラートメッセージ |
| severity | string | No | "info" | 重要度（`info` / `warning` / `critical`） |
| source | string | No | null | アラートソース（任意の識別文字列） |

- **レスポンス**: `201 Created` - `AlertResponse`
- **エラー**: `422 Unprocessable Entity` - バリデーションエラー（severity 不正等）

**リクエスト例:**

```json
{
  "title": "Deploy Notification",
  "message": "Production deploy scheduled at 22:00",
  "severity": "warning",
  "source": "deploy-system"
}
```

**手動作成アラートの特徴:**
- `rule_id` は `null`（ルール起因ではない）
- `is_active` は `true`（初期状態）
- `acknowledged` は `false`（未確認）

### 3.4 GET /api/alerts/{id}

指定IDのアラートを取得する。

- **権限**: 認証済みユーザー
- **パスパラメータ**: `id` (integer) - アラートID
- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found` - アラート不存在

### 3.5 PATCH /api/alerts/{id}/acknowledge

アラートを確認済みにマークする。確認者のユーザーIDと確認日時が記録される。

- **権限**: 認証済みユーザー（確認者として `user_id` が記録される）
- **パスパラメータ**: `id` (integer) - アラートID
- **リクエストボディ**: なし
- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found` - アラート不存在

**確認時に設定されるフィールド:**

| フィールド | 値 |
|------------|-----|
| acknowledged | true |
| acknowledged_by | 操作ユーザーの user_id |
| acknowledged_at | 現在日時（UTC） |

**レスポンス例:**

```json
{
  "id": 1,
  "title": "ERROR in prod-server",
  "message": "Database connection failed",
  "severity": "critical",
  "source": "prod-server",
  "rule_id": 1,
  "is_active": true,
  "acknowledged": true,
  "acknowledged_by": 1,
  "acknowledged_at": "2026-02-12T11:00:00+00:00",
  "created_at": "2026-02-12T10:30:00+09:00"
}
```

### 3.6 PATCH /api/alerts/{id}/deactivate

アラートを非アクティブに変更する。非アクティブなアラートは `active_only=true` のフィルタで除外される。

- **権限**: 認証済みユーザー
- **パスパラメータ**: `id` (integer) - アラートID
- **リクエストボディ**: なし
- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found` - アラート不存在

**非活性化時に設定されるフィールド:**

| フィールド | 値 |
|------------|-----|
| is_active | false |

### 3.7 DELETE /api/alerts/{id}

アラートを物理削除する。

- **権限**: admin のみ（非admin は `403 Forbidden`）
- **パスパラメータ**: `id` (integer) - アラートID
- **レスポンス**: `204 No Content`
- **エラー**:
  - `403 Forbidden` - admin 以外のユーザー
  - `404 Not Found` - アラート不存在

---

## 4. スキーマ

### 4.1 AlertCreate

```python
class AlertCreate(BaseModel):
    title: str
    message: str
    severity: Literal["info", "warning", "critical"] = "info"
    source: Optional[str] = None
```

### 4.2 AlertResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | アラートID |
| title | string | アラートタイトル |
| message | string | アラートメッセージ |
| severity | string | 重要度（`info` / `warning` / `critical`） |
| source | string \| null | アラートソース |
| rule_id | integer \| null | 自動生成元ルールID（手動作成は null） |
| is_active | boolean | アクティブフラグ |
| acknowledged | boolean | 確認済みフラグ |
| acknowledged_by | integer \| null | 確認者の user_id |
| acknowledged_at | datetime \| null | 確認日時 |
| created_at | datetime | 発生日時 |

### 4.3 AlertCountResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| count | integer | 未確認アラート件数 |

---

## 5. Severity（重要度）仕様

### 5.1 有効な値

| 値 | 説明 | UI表示色 |
|----|------|---------|
| `info` | 情報（デフォルト） | 水色 (`bg-info`) |
| `warning` | 警告 | 黄色 (`bg-warning`) |
| `critical` | 致命的 | 赤 (`bg-danger`) |

### 5.2 バリデーション

- `Literal["info", "warning", "critical"]` で厳密に検証
- 大文字混在（`Warning`）→ 422
- 空文字 → 422
- 未知の値（`INVALID`）→ 422
- 全3値（`info`, `warning`, `critical`）が受け入れられることをテストで確認

---

## 6. アラートの状態遷移

### 6.1 状態フラグ

アラートは2つの独立したフラグで状態を管理する:

| フラグ | 初期値 | 説明 |
|--------|--------|------|
| `is_active` | true | アクティブ/非アクティブ |
| `acknowledged` | false | 未確認/確認済み |

### 6.2 状態遷移図

```
[作成]
  ↓
is_active=true, acknowledged=false  (未確認・アクティブ)
  ├── PATCH /acknowledge → is_active=true, acknowledged=true  (確認済み・アクティブ)
  └── PATCH /deactivate → is_active=false, acknowledged=false (未確認・非アクティブ)
```

- 確認と非活性化は独立した操作であり、両方を適用可能
- 未確認件数カウント: `acknowledged=false` AND `is_active=true` の件数

### 6.3 フィルタリングへの影響

| フィルタ | 対象 |
|---------|------|
| `active_only=false`（デフォルト） | 全アラート |
| `active_only=true` | `is_active=true` のアラートのみ |
| 未確認カウント | `acknowledged=false` AND `is_active=true` |

---

## 7. WebSocket 連携

### 7.1 リアルタイム通知

アラート生成時（手動作成・ルール自動生成の両方）に、WebSocket `/ws/alerts` を通じて全接続クライアントにブロードキャストされる。

**通知メッセージ形式:**

```json
{
  "type": "new_alert",
  "alert": {
    "id": 1,
    "title": "ERROR in prod-server",
    "message": "Database connection failed",
    "severity": "critical",
    "source": "prod-server",
    "rule_id": 1,
    "is_active": true,
    "acknowledged": false,
    "created_at": "2026-02-12T10:30:00+09:00"
  }
}
```

### 7.2 ナビバッジ

`base.html` のグローバルスクリプトが以下の動作を行う:

1. ページロード時に `GET /api/alerts/count` で未確認件数を取得
2. WebSocket `/ws/alerts` に接続し、`onmessage` で新着アラートを検知
3. 新着検知時に `GET /api/alerts/count` を再取得してバッジを更新
4. 未確認件数 > 0 の場合、バッジ（赤い丸数字）を表示
5. 未確認件数 = 0 の場合、バッジを非表示

**バッジ HTML:**

```html
<span class="badge bg-danger rounded-pill d-none" id="alert-badge">0</span>
```

### 7.3 WebSocket 再接続

- 切断検知後5秒で自動再接続（`setTimeout(connectAlertBadgeWs, 5000)`）
- Alerts画面のアラート用WebSocketは3秒で再接続

---

## 8. データベース

### 8.1 alerts テーブル

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | アラートID |
| title | String(500) | NOT NULL | アラートタイトル |
| message | Text | NOT NULL | アラートメッセージ |
| severity | String(20) | NOT NULL, DEFAULT "info" | 重要度 |
| source | String(200) | NULL許可 | アラートソース |
| rule_id | Integer | FK(alert_rules.id, SET NULL), NULL許可 | 自動生成元ルールID |
| is_active | Boolean | NOT NULL, DEFAULT true | アクティブフラグ |
| acknowledged | Boolean | NOT NULL, DEFAULT false | 確認済みフラグ |
| acknowledged_by | Integer | FK(users.id, SET NULL), NULL許可 | 確認者の user_id |
| acknowledged_at | DateTime(TZ) | NULL許可 | 確認日時 |
| created_at | DateTime(TZ) | DEFAULT now() | 発生日時 |

### 8.2 リレーション

| FK | 参照先 | ON DELETE |
|----|--------|----------|
| `rule_id` | `alert_rules.id` | SET NULL（ルール削除時に null） |
| `acknowledged_by` | `users.id` | SET NULL（ユーザー削除時に null） |

### 8.3 クエリパターン

| 操作 | ソート/フィルタ |
|------|----------------|
| 一覧取得 | `ORDER BY created_at DESC LIMIT ?` |
| アクティブのみ | `WHERE is_active = true ORDER BY created_at DESC LIMIT ?` |
| 未確認件数 | `WHERE acknowledged = false AND is_active = true` の COUNT |

---

## 9. フロントエンド

### 9.1 画面構成

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/alerts.html` |
| JavaScript | `static/js/alerts.js` |
| ルーター | `app/routers/pages.py` (`GET /alerts`) |

### 9.2 Alerts画面レイアウト

Alerts画面は2つのセクションで構成される:

**上部: アラート一覧**
- WebSocket接続状態バッジ（Connected: 緑 / Disconnected: 赤）
- フィルタボタン: All（デフォルト）/ Active
- Create Alert ボタン → モーダル
- アラートカード一覧（重要度による色分けボーダー）

**下部: アラートルール管理**（詳細は [SPEC_alert-rules.md](../alert-rules/SPEC_alert-rules.md) を参照）

### 9.3 アラートカード表示

各アラートカードに以下を表示:

| 要素 | 内容 |
|------|------|
| 重要度バッジ | `critical`=赤, `warning`=黄, `info`=水色 |
| タイトル | 太字で表示 |
| ソース | `[source]` 形式で表示（設定時のみ） |
| 自動生成バッジ | `rule_id` が存在する場合 `auto` バッジを表示 |
| メッセージ | カード本文に表示 |
| 作成日時 | `toLocaleString()` でローカル日時表示 |
| 操作ボタン | Acknowledge / Deactivate（状態に応じて表示切替） |

**カード状態表示:**
- アクティブ + 未確認: Acknowledge ボタン + Deactivate ボタン
- アクティブ + 確認済み: `Acknowledged` バッジ + Deactivate ボタン
- 非アクティブ: `Inactive` バッジ（半透明表示）

### 9.4 Create Alert モーダル

| フィールド | 入力タイプ | デフォルト | 説明 |
|------------|-----------|-----------|------|
| Title | テキスト | - | アラートタイトル（必須） |
| Message | テキストエリア | - | アラートメッセージ（必須） |
| Severity | セレクト | warning | 重要度（info / warning / critical） |
| Source | テキスト | - | アラートソース（任意） |

### 9.5 JavaScript API

| 関数 | 説明 |
|------|------|
| `loadAlerts()` | `GET /api/alerts/` でアラート一覧を取得・描画 |
| `renderAlerts()` | アラートカードをHTML生成 |
| `filterAlerts(filter, btn)` | `all` / `active` フィルタ切替 |
| `createAlert()` | `POST /api/alerts/` でアラート作成 |
| `acknowledgeAlert(id)` | `PATCH /api/alerts/{id}/acknowledge` で確認 |
| `deactivateAlert(id)` | `PATCH /api/alerts/{id}/deactivate` で非活性化 |
| `alertSeverityColor(s)` | severity → Bootstrap 色クラス変換 |
| `connectAlertWebSocket()` | `/ws/alerts` WebSocket接続、新着時にリスト先頭に追加 |

### 9.6 WebSocket 受信処理

```javascript
alertWs.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'new_alert') {
        allAlerts.unshift(data.alert);  // リスト先頭に追加
        renderAlerts();                  // 再描画
    }
};
```

---

## 10. 実装ファイル一覧

| レイヤー | ファイル | 説明 |
|---------|---------|------|
| ルーター | `app/routers/api_alerts.py` | HTTPエンドポイント定義（7エンドポイント、全 async） |
| サービス | `app/services/alert_service.py` | アラートCRUD + WebSocket通知（ルール評価エンジンと共用） |
| CRUD | `app/crud/alert.py` | DB操作（alerts + alert_rules 共用） |
| スキーマ | `app/schemas/alert.py` | Pydantic バリデーション（severity Literal 検証） |
| モデル | `app/models/alert.py` | SQLAlchemy ORM定義（Alert + AlertRule 共用） |
| WebSocket | `app/services/websocket_manager.py` | `alert_ws_manager` による接続管理・ブロードキャスト |
| テスト | `tests/test_alerts.py` | 16テストケース（3クラス） |
| フロントエンド | `static/js/alerts.js` | アラート一覧・作成・確認・非活性化のクライアント実装 |
| ナビバッジ | `templates/base.html` | 全ページ共通の未確認バッジ更新スクリプト |

---

## 11. テスト仕様

### 11.1 テスト構成

| テストクラス | テスト数 | 内容 |
|-------------|---------|------|
| TestAlertAPI | 11 | 基本CRUD + 確認 + 非活性化 + カウント |
| TestAlertSeverityValidation | 4 | severity バリデーション |
| TestAlertRBAC | 1 | 権限制御（削除） |
| **合計** | **16** | |

### 11.2 テストケース一覧

#### 基本操作テスト (TestAlertAPI)

| テストケース | 検証内容 |
|-------------|---------|
| test_create_alert | 手動アラート作成（201 + AlertResponse、is_active=true, acknowledged=false） |
| test_default_severity | デフォルト severity が `info` |
| test_list_alerts | アラート一覧取得（複数件） |
| test_list_active_only | `active_only=true` フィルタの動作（非アクティブが除外される） |
| test_get_alert | ID指定でアラート取得 |
| test_get_alert_not_found | 存在しないIDで404 |
| test_acknowledge_alert | アラート確認（acknowledged=true, acknowledged_by, acknowledged_at 設定） |
| test_deactivate_alert | アラート非活性化（is_active=false） |
| test_unacknowledged_count | 未確認件数の算出（確認済みを除外） |
| test_delete_alert | アラート削除（admin、204 + 取得で404） |
| test_delete_alert_not_found | 存在しないアラート削除で404 |

#### Severity バリデーション テスト (TestAlertSeverityValidation)

| テストケース | 検証内容 |
|-------------|---------|
| test_valid_severities | 有効な severity 値（info/warning/critical）がすべて受け入れられる |
| test_invalid_severity_rejected | 不正な severity `"INVALID"` で422 |
| test_empty_severity_rejected | 空文字 severity で422 |
| test_mixed_case_severity_rejected | 大文字混在 `"Warning"` で422 |

#### RBAC テスト (TestAlertRBAC)

| テストケース | 検証内容 |
|-------------|---------|
| test_non_admin_cannot_delete_alert | 非adminでアラート削除403 |

### 11.3 テスト実行

```bash
pytest tests/test_alerts.py -q
```

---

## 12. 設定

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `API_ALERT_LIMIT` | 100 | `GET /api/alerts/` のデフォルト取得件数上限 |

---

## 13. 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [SPEC_alert-rules.md](../alert-rules/SPEC_alert-rules.md) | アラートルール API 仕様（自動アラート生成の条件定義） |
| [SPEC_API.md](../../SPEC_API.md) | API仕様（全エンドポイント概要） |
| [../ws/alerts/](../../ws/) | WebSocket `/ws/alerts` 仕様 |
