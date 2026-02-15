# Alert 機能仕様書

> システムアラート管理機能の完全な仕様。アラートルール定義・自動アラート生成・手動アラート作成・WebSocket リアルタイム通知・ナビバーバッジを含む。

---

## 1. 概要

### 1.1 背景

システムログや外部イベントに基づいて、重要な事象を検知・通知するためのアラート機能。
条件ベースのアラートルールを定義し、ログ取り込み時に自動評価してアラートを生成する。
手動でのアラート作成も可能。

### 1.2 目的

- アラートルールによるログベースの自動アラート生成
- 手動アラートの作成
- Acknowledge（確認）/ Deactivate（無効化）によるアラートライフサイクル管理
- WebSocket によるリアルタイム通知（アラート画面 + ナビバーバッジ）
- 未確認アラート数のバッジ表示（全ページ共通）

### 1.3 基本フロー

```
[ログ取り込み]
    ↓
log_service.create_log()
    ↓
alert_service.evaluate_rules_for_log()
    ↓ (有効ルールの condition と一致)
Alert 自動生成 → WebSocket broadcast → ナビバーバッジ更新 + アラート画面リアルタイム追加
    ↓
ユーザー → Acknowledge / Deactivate

[手動アラート]
ユーザー → Create Alert モーダル → POST /api/alerts/ → WebSocket broadcast
```

### 1.4 主要用語

| 用語 | 説明 |
|------|------|
| AlertRule | アラート生成条件の定義。ログデータに対する条件マッチングとテンプレートベースのアラート生成 |
| Alert | 生成されたアラート。手動作成（`rule_id=null`）と自動生成（`rule_id` あり）の 2 種類 |
| Condition | JSON 形式のマッチング条件。完全一致・`$in`・`$contains` 演算子をサポート |
| Acknowledge | アラートの確認。誰がいつ確認したかを記録 |
| Deactivate | アラートの無効化。一覧表示で半透明になる |
| Severity | アラートの重要度：`info` / `warning` / `critical` |

---

## 2. データモデル

### 2.1 AlertRule テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| `id` | Integer | PK, AUTO | ルール ID |
| `name` | String(200) | NOT NULL | ルール名 |
| `condition` | JSON | NOT NULL | マッチング条件（PostgreSQL JSON 型） |
| `alert_title_template` | String(500) | NOT NULL | アラートタイトルテンプレート |
| `alert_message_template` | Text | NULL 許容 | アラートメッセージテンプレート |
| `severity` | String(20) | NOT NULL, default `"warning"` | 生成アラートの重要度 |
| `is_enabled` | Boolean | NOT NULL, default `True` | ルールの有効/無効 |
| `created_at` | DateTime(TZ) | server_default `now()` | 作成日時 |
| `updated_at` | DateTime(TZ) | server_default `now()`, onupdate | 更新日時 |

### 2.2 Alert テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| `id` | Integer | PK, AUTO | アラート ID |
| `title` | String(500) | NOT NULL | アラートタイトル |
| `message` | Text | NOT NULL | アラートメッセージ |
| `severity` | String(20) | NOT NULL, default `"info"` | 重要度 |
| `source` | String(200) | NULL 許容 | ソース（system_name） |
| `rule_id` | Integer | FK → `alert_rules.id` (SET NULL) | 生成元ルール ID（手動作成時は NULL） |
| `is_active` | Boolean | NOT NULL, default `True` | アクティブ状態 |
| `acknowledged` | Boolean | NOT NULL, default `False` | 確認済みフラグ |
| `acknowledged_by` | Integer | FK → `users.id` (SET NULL) | 確認したユーザー ID |
| `acknowledged_at` | DateTime(TZ) | NULL 許容 | 確認日時 |
| `created_at` | DateTime(TZ) | server_default `now()` | 作成日時 |

### 2.3 ER 図

```
alert_rules (1) ----< (0..*) alerts
                          rule_id FK (SET NULL)

users (1) ----< (0..*) alerts
                    acknowledged_by FK (SET NULL)
```

---

## 3. API エンドポイント

### 3.1 Alert API (`/api/alerts`)

| メソッド | パス | 認可 | 説明 |
|---------|------|------|------|
| `GET` | `/api/alerts/` | 認証ユーザー | アラート一覧取得 |
| `GET` | `/api/alerts/count` | 認証ユーザー | 未確認アラート数 |
| `POST` | `/api/alerts/` | 認証ユーザー | 手動アラート作成 |
| `GET` | `/api/alerts/{id}` | 認証ユーザー | アラート詳細取得 |
| `PATCH` | `/api/alerts/{id}/acknowledge` | 認証ユーザー | アラート確認 |
| `PATCH` | `/api/alerts/{id}/deactivate` | 認証ユーザー | アラート無効化 |
| `DELETE` | `/api/alerts/{id}` | **Admin のみ** | アラート削除 |

#### GET /api/alerts/

クエリパラメータ:

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `active_only` | bool | `false` | `true` の場合、`is_active=True` のみ返す |
| `limit` | int | `100` | 取得件数上限 |

レスポンス: `AlertResponse[]`（`created_at` 降順）

#### GET /api/alerts/count

レスポンス: `{"count": N}`（`acknowledged=False` かつ `is_active=True` の件数）

#### PATCH /api/alerts/{id}/acknowledge

- `acknowledged = True` に更新
- `acknowledged_by` にリクエストユーザー ID を記録
- `acknowledged_at` に現在時刻（UTC）を記録

#### PATCH /api/alerts/{id}/deactivate

- `is_active = False` に更新

### 3.2 Alert Rule API (`/api/alert-rules`)

| メソッド | パス | 認可 | 説明 |
|---------|------|------|------|
| `GET` | `/api/alert-rules/` | 認証ユーザー | ルール一覧取得 |
| `POST` | `/api/alert-rules/` | **Admin のみ** | ルール作成 |
| `GET` | `/api/alert-rules/{id}` | 認証ユーザー | ルール詳細取得 |
| `PUT` | `/api/alert-rules/{id}` | **Admin のみ** | ルール更新 |
| `DELETE` | `/api/alert-rules/{id}` | **Admin のみ** | ルール削除 |

### 3.3 WebSocket (`/ws/alerts`)

| パス | 認証 | 説明 |
|------|------|------|
| `/ws/alerts` | セッション認証 | アラートリアルタイム通知 |

- 未認証の場合 `code=4401` で close
- アラート作成時に `{"type": "new_alert", "alert": {...}}` を全クライアントにブロードキャスト
- アラート画面とナビバーバッジの両方が接続

---

## 4. スキーマ定義

### 4.1 Severity

```python
ALERT_SEVERITIES = ("info", "warning", "critical")
AlertSeverity = Literal["info", "warning", "critical"]
```

- 小文字のみ有効（`"Warning"` は 422 エラー）
- 空文字列は 422 エラー

### 4.2 Condition バリデーション

```python
VALID_CONDITION_OPERATORS = {"$in", "$contains"}
```

| ルール | 説明 |
|--------|------|
| 空の dict `{}` は拒否 | condition は最低 1 つのフィールドが必要 |
| キーは文字列のみ | `isinstance(field, str)` チェック |
| 値がリスト/タプルは拒否 | `{"severity": [1, 2]}` → 422 エラー |
| 値が dict の場合、キーは `$in` / `$contains` のみ | 不明な演算子 → 422 エラー |
| 演算子 dict が空は拒否 | `{"severity": {}}` → 422 エラー |

### 4.3 AlertRule スキーマ

**AlertRuleCreate:**

| フィールド | 型 | デフォルト | 必須 |
|-----------|-----|----------|------|
| `name` | str | - | Yes |
| `condition` | dict | - | Yes（バリデーションあり） |
| `alert_title_template` | str | - | Yes |
| `alert_message_template` | str | `None` | No |
| `severity` | AlertSeverity | `"warning"` | No |
| `is_enabled` | bool | `True` | No |

**AlertRuleUpdate:** 全フィールド Optional（`exclude_unset=True` で部分更新）

**AlertRuleResponse:** `id`, `name`, `condition`, `alert_title_template`, `alert_message_template`, `severity`, `is_enabled`, `created_at`, `updated_at`

### 4.4 Alert スキーマ

**AlertCreate:**

| フィールド | 型 | デフォルト | 必須 |
|-----------|-----|----------|------|
| `title` | str | - | Yes |
| `message` | str | - | Yes |
| `severity` | AlertSeverity | `"info"` | No |
| `source` | str | `None` | No |

**AlertResponse:** `id`, `title`, `message`, `severity`, `source`, `rule_id`, `is_active`, `acknowledged`, `acknowledged_by`, `acknowledged_at`, `created_at`

**AlertCountResponse:** `count` (int)

---

## 5. ルール評価エンジン

### 5.1 概要

ログ取り込み時に `log_service.create_log()` が `alert_service.evaluate_rules_for_log()` を呼び出し、有効な全ルールをログデータに対して評価する。

### 5.2 条件マッチング (`_matches_condition`)

全条件が AND 論理で評価される。1 つでもマッチしなければ `False`。

| パターン | 条件例 | マッチするデータ |
|---------|--------|-----------------|
| 完全一致 | `{"severity": "ERROR"}` | `{"severity": "ERROR", ...}` |
| `$in` 演算子 | `{"severity": {"$in": ["ERROR", "CRITICAL"]}}` | `{"severity": "ERROR"}` |
| `$contains` 演算子 | `{"message": {"$contains": "database"}}` | `{"message": "database connection failed"}` |
| AND 結合 | `{"severity": "ERROR", "system_name": "app"}` | 両方一致で `True` |

マッチング時の特殊ケース:

- ログデータに該当フィールドがない → `False`（マッチしない）
- 不明な演算子（`$unknown` など） → `False`（マッチしない）
- `$contains` は `str(actual)` で文字列変換後に部分一致チェック

### 5.3 テンプレート変数展開 (`_safe_substitute`)

```python
# テンプレート例
alert_title_template = "{severity} in {system_name}"
# ログデータ
log_data = {"severity": "ERROR", "system_name": "prod-server", "message": "disk full"}
# 結果
title = "ERROR in prod-server"
```

変換プロセス:

1. `{variable}` 形式を `${variable}` 形式に正規表現で変換
2. `string.Template.safe_substitute()` で安全に展開
3. 未定義の変数はそのまま残る（`safe_substitute` の挙動）
4. `None` 値は空文字列に変換
5. 例外発生時はテンプレート文字列をそのまま返す

> `str.format_map()` ではなく `string.Template` を使用する理由: フォーマット文字列インジェクションの防止

### 5.4 自動アラート生成フロー

```
evaluate_rules_for_log(db, log_data)
    ↓
get_enabled_alert_rules(db) — is_enabled=True のルールのみ取得
    ↓
for each rule:
    ↓
    _matches_condition(rule.condition, log_data)
        ↓ True
    title = _safe_substitute(rule.alert_title_template, log_data)
    message = rule.alert_message_template ? _safe_substitute(...) : log_data["message"]
        ↓
    AlertCreate(title, message, severity=rule.severity, source=log_data["system_name"])
        ↓
    crud_alert.create_alert(db, data, rule_id=rule.id)
        ↓
    _broadcast_alert(alert) → WebSocket
```

- 1 つのログが複数ルールにマッチ可能 → 複数アラートが生成される
- 無効（`is_enabled=False`）のルールは評価されない
- `source` にはログの `system_name` が設定される

---

## 6. WebSocket 通知

### 6.1 アーキテクチャ

```
alert_ws_manager (WebSocketManager インスタンス)
    ↓ broadcast()
[アラート画面の WebSocket] + [ナビバーバッジの WebSocket]
```

- `WebSocketManager`: `connect()` / `disconnect()` / `broadcast()` を持つ共通クラス
- `alert_ws_manager` はモジュールレベルのシングルトンインスタンス
- 切断されたコネクションは `broadcast()` 内で自動除去

### 6.2 ブロードキャストメッセージ

```json
{
    "type": "new_alert",
    "alert": {
        "id": 1,
        "title": "ERROR in prod-server",
        "message": "Database connection failed",
        "severity": "critical",
        "source": "prod-server",
        "rule_id": 3,
        "is_active": true,
        "acknowledged": false,
        "created_at": "2026-02-10T12:00:00+09:00"
    }
}
```

### 6.3 接続元

| 接続元 | 目的 | 再接続間隔 |
|--------|------|-----------|
| アラート画面 (`alerts.js`) | 新規アラートのリアルタイム表示 | 3 秒 |
| ナビバーバッジ (`base.html`) | 未確認カウント更新 | 5 秒 |

---

## 7. フロントエンド

### 7.1 画面構成

`/alerts` ページは上下 2 セクションで構成:

1. **Alerts セクション**（上部）
   - WebSocket 接続状態バッジ（Connected/Disconnected）
   - All / Active フィルターボタン
   - Create Alert ボタン → モーダル
   - アラートカード一覧

2. **Alert Rules セクション**（下部）
   - ルール管理テーブル（Name, Condition, Severity, Status, Actions）
   - Add Rule ボタン → モーダル

### 7.2 アラートカード

各アラートはカードとして表示:

- Severity バッジ（色分け: `critical` → danger, `warning` → warning, `info` → info）
- タイトル + ソース表示
- `rule_id` があれば `auto` バッジ（自動生成の識別）
- Acknowledge ボタン（未確認 + アクティブ時のみ）
- Deactivate ボタン（アクティブ時のみ）
- 非アクティブカードは `opacity-50` で半透明
- メッセージ + 作成日時

### 7.3 ルールテーブル

各ルールは行で表示:

- Name, Condition（JSON, `<code>` タグ）, Severity バッジ, Status（Enabled/Disabled）
- Actions: Edit（モーダル）/ Toggle（有効/無効切替）/ Delete（confirm ダイアログ）

### 7.4 ルールモーダル

入力フィールド:

- Rule Name (text)
- Alert Severity (select: info/warning/critical)
- Condition (textarea, JSON 入力。プレースホルダー `{"severity": "ERROR"}`)
- Title Template (text, プレースホルダー `{severity} in {system_name}`)
- Message Template (text, optional)
- Enabled (checkbox)

JSON パースエラー時は `showToast('Invalid JSON in condition')` を表示。

### 7.5 ナビバーバッジ

`base.html` に組み込まれ、全ページ共通で動作:

```html
<span class="badge bg-danger rounded-pill d-none" id="alert-badge">0</span>
```

- ページ読み込み時に `GET /api/alerts/count` で初期値取得
- WebSocket `/ws/alerts` に接続し、`onmessage` で `loadAlertCount()` を再実行
- `count > 0` で表示、`count == 0` で `d-none` 非表示

### 7.6 JavaScript 関数

**alerts.js:**

| 関数 | 説明 |
|------|------|
| `loadAlerts()` | API からアラート一覧取得。フィルターに応じて `?active_only=true` |
| `renderAlerts()` | カード一覧を DOM に描画 |
| `filterAlerts(filter, btn)` | All/Active フィルター切替 |
| `createAlert()` | モーダルから手動アラート作成 |
| `acknowledgeAlert(id)` | アラート確認 |
| `deactivateAlert(id)` | アラート無効化 |
| `alertSeverityColor(s)` | severity → Bootstrap カラークラス変換 |
| `loadRules()` | ルール一覧取得 |
| `renderRules(rules)` | ルールテーブル描画 |
| `openRuleModal(rule)` | ルールモーダルの初期化（新規/編集） |
| `editRule(id)` | ルール編集モーダル表示 |
| `saveRule()` | ルール保存（新規: POST / 編集: PUT） |
| `toggleRule(id, enabled)` | ルール有効/無効切替 |
| `deleteRule(id)` | ルール削除（confirm 付き） |
| `connectAlertWebSocket()` | WebSocket 接続 + 再接続ロジック |

**base.html (ナビバー):**

| 関数 | 説明 |
|------|------|
| `updateAlertBadge(count)` | バッジの表示/非表示切替 |
| `loadAlertCount()` | `GET /api/alerts/count` でカウント取得 |
| `connectAlertBadgeWs()` | バッジ用 WebSocket 接続 |

---

## 8. 認可ルール

| 操作 | 必要権限 | 実装 |
|------|---------|------|
| アラート一覧・詳細・カウント | 認証ユーザー | `Depends(get_current_user_id)` |
| アラート作成（手動） | 認証ユーザー | `Depends(get_current_user_id)` |
| アラート確認 (Acknowledge) | 認証ユーザー | `Depends(get_current_user_id)`、user_id を記録 |
| アラート無効化 (Deactivate) | 認証ユーザー | `Depends(get_current_user_id)` |
| アラート削除 | **Admin のみ** | `Depends(require_admin)` |
| ルール一覧・詳細 | 認証ユーザー | `Depends(get_current_user_id)` |
| ルール作成・更新・削除 | **Admin のみ** | `Depends(require_admin)` |

---

## 9. ログ連携

### 9.1 連携フロー

```python
# app/services/log_service.py
async def create_log(db, data):
    log = crud_log.create_log(db, data)
    await log_ws_manager.broadcast(log_dict)
    await alert_service.evaluate_rules_for_log(db, log_dict)  # ← ここ
    return log
```

### 9.2 評価対象データ

`log_dict` は以下のフィールドを含む:

| フィールド | ソース | テンプレートで使用可能 |
|-----------|--------|---------------------|
| `id` | Log.id | Yes |
| `system_name` | Log.system_name | Yes（`source` にも使用） |
| `log_type` | Log.log_type | Yes |
| `severity` | Log.severity | Yes |
| `message` | Log.message | Yes（デフォルトメッセージ） |
| `received_at` | Log.received_at | Yes |

### 9.3 ログ取り込み API

`POST /api/logs/` は認証不要（外部システムからのログ取り込み用）。
この API 経由のログもアラートルール評価の対象となる。

---

## 10. ビジネスルール

### 10.1 アラートライフサイクル

```
作成 (is_active=True, acknowledged=False)
  ↓
Acknowledge → acknowledged=True, acknowledged_by=user_id, acknowledged_at=now
  ↓ or
Deactivate → is_active=False
  ↓ or
Delete → 物理削除（Admin のみ）
```

- Acknowledge と Deactivate は独立した操作（両方実行可能）
- Deactivate されたアラートは `active_only=true` フィルターで除外
- 非アクティブカードは UI で半透明表示
- 削除されたルール(`ondelete="SET NULL"`) → アラートの `rule_id` が NULL になるが、アラート自体は残る

### 10.2 ルール有効/無効

- `is_enabled=True` のルールのみが `evaluate_rules_for_log()` で評価される
- 無効化はルール更新 API で `is_enabled: false` を送信
- 無効ルールは UI で Disabled バッジ表示、Play ボタンで再有効化可能

### 10.3 複数ルールマッチ

1 つのログエントリが複数のルールの condition にマッチする場合、それぞれのルールから個別のアラートが生成される。

---

## 11. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/alert.py` | `AlertRule`, `Alert` モデル定義 |
| `app/schemas/alert.py` | スキーマ定義 + condition バリデーション + severity 型 |
| `app/crud/alert.py` | DB アクセス（ルール CRUD + アラート CRUD） |
| `app/services/alert_service.py` | ビジネスロジック + ルール評価エンジン + WebSocket ブロードキャスト |
| `app/services/log_service.py` | ログ作成後のアラートルール評価呼び出し |
| `app/services/websocket_manager.py` | `WebSocketManager` クラス + `alert_ws_manager` インスタンス |
| `app/routers/api_alerts.py` | Alert REST API（7 エンドポイント） |
| `app/routers/api_alert_rules.py` | Alert Rule REST API（5 エンドポイント） |
| `main.py` | `/ws/alerts` WebSocket エンドポイント |
| `templates/alerts.html` | アラート画面テンプレート（モーダル 2 つ含む） |
| `templates/base.html` | ナビバーバッジ + バッジ用 WebSocket |
| `static/js/alerts.js` | アラート画面 JS（アラート管理 + ルール管理 + WebSocket） |
| `tests/test_alerts.py` | Alert API テスト（16 テスト） |
| `tests/test_alert_rules.py` | Alert Rule API + ルール評価テスト（29 テスト） |
| `alembic/versions/82739a6351f7_...` | マイグレーション: `alert_rules` + `alerts` テーブル作成 |

---

## 12. テスト

### 12.1 Alert API テスト（`tests/test_alerts.py` — 16 テスト）

**TestAlertAPI (11 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_create_alert` | 手動アラート作成、デフォルト値確認 |
| `test_default_severity` | severity 未指定時に `"info"` がデフォルト |
| `test_list_alerts` | 一覧取得 |
| `test_list_active_only` | `active_only=true` フィルター |
| `test_get_alert` | 個別取得 |
| `test_get_alert_not_found` | 存在しない ID → 404 |
| `test_acknowledge_alert` | Acknowledge 処理（acknowledged, acknowledged_by, acknowledged_at） |
| `test_deactivate_alert` | Deactivate 処理（is_active=False） |
| `test_unacknowledged_count` | 未確認カウント（Acknowledge 済みを除外） |
| `test_delete_alert` | Admin によるアラート削除 |
| `test_delete_alert_not_found` | 存在しない ID の削除 → 404 |

**TestAlertSeverityValidation (4 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_invalid_severity_rejected` | 不正な severity → 422 |
| `test_empty_severity_rejected` | 空文字列 → 422 |
| `test_mixed_case_severity_rejected` | 大文字混在 `"Warning"` → 422 |
| `test_valid_severities` | `info`, `warning`, `critical` がすべて 201 |

**TestAlertRBAC (1 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_non_admin_cannot_delete_alert` | 非 Admin ユーザーの削除 → 403 |

### 12.2 Alert Rule テスト（`tests/test_alert_rules.py` — 29 テスト）

**TestAlertRuleCRUD (7 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_create_rule` | ルール作成 + デフォルト値 |
| `test_list_rules` | 一覧取得 |
| `test_get_rule` | 個別取得 |
| `test_get_rule_not_found` | 存在しない ID → 404 |
| `test_update_rule` | 部分更新（name のみ変更） |
| `test_delete_rule` | ルール削除 + 削除確認 |
| `test_toggle_rule` | `is_enabled` の切替 |

**TestAlertRuleSeverityValidation (2 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_invalid_rule_severity_rejected` | 不正な severity → 422 |
| `test_empty_rule_severity_rejected` | 空文字列 → 422 |

**TestAlertRuleConditionValidation (5 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_empty_condition_rejected` | 空 dict → 422 |
| `test_unknown_operator_rejected` | 不明演算子 `$unknown` → 422 |
| `test_list_value_rejected` | リスト値 → 422 |
| `test_valid_in_operator_accepted` | `$in` 演算子 → 201 |
| `test_valid_contains_operator_accepted` | `$contains` 演算子 → 201 |

**TestAlertRuleRBAC (4 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_non_admin_cannot_create_rule` | 非 Admin → 403 |
| `test_non_admin_cannot_update_rule` | 非 Admin → 403 |
| `test_non_admin_cannot_delete_rule` | 非 Admin → 403 |
| `test_non_admin_can_read_rules` | 非 Admin でも一覧取得は 200 |

**TestRuleEvaluation (7 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_exact_match` | 完全一致マッチング |
| `test_no_match` | 不一致 |
| `test_in_operator` | `$in` 演算子（マッチ + 不一致） |
| `test_contains_operator` | `$contains` 演算子（部分一致 + 不一致） |
| `test_multiple_conditions_and` | 複数条件 AND 結合 |
| `test_missing_field_no_match` | フィールド欠損 → 不一致 |
| `test_unknown_operator_no_match` | 不明演算子 → 不一致 |

**TestRuleEvaluationIntegration (4 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_log_triggers_alert` | ログ → ルール評価 → アラート自動生成 |
| `test_disabled_rule_no_alert` | 無効ルールはアラートを生成しない |
| `test_template_variables` | テンプレート変数の展開確認 |
| `test_multiple_rules_match_same_log` | 1 ログで複数ルールマッチ → 複数アラート |

---

## 13. マイグレーション

| リビジョン | 説明 | 依存 |
|-----------|------|------|
| `82739a6351f7` | `alert_rules` + `alerts` テーブル作成 | `6ee8442a6984` |

### 作成されるテーブル

**alert_rules:**
- PK: `id` (Integer, autoincrement)
- `condition`: PostgreSQL `JSON` 型
- `severity` default: なし（モデル側で `"warning"`）
- `is_enabled` default: なし（モデル側で `True`）
- `created_at` / `updated_at`: `server_default=now()`

**alerts:**
- PK: `id` (Integer, autoincrement)
- FK: `rule_id` → `alert_rules.id` (SET NULL)
- FK: `acknowledged_by` → `users.id` (SET NULL)
- `is_active` / `acknowledged`: NOT NULL Boolean
- `created_at`: `server_default=now()`
