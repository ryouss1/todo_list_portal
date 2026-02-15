# Alert Rules API 仕様書

> 本ドキュメントは [SPEC_API.md](../../SPEC_API.md) の補足資料です。

## 1. 概要

アラートルールは、ログ登録時に自動でアラートを生成するための条件定義を管理する機能である。
管理者が条件（condition）、テンプレート、重要度を指定してルールを作成し、`POST /api/logs/` でログが登録されるたびに有効なルールが評価される。条件に一致した場合、アラートが自動生成され、WebSocket (`/ws/alerts`) 経由で全クライアントに通知される。

### 1.1 機能一覧

| 機能 | 説明 |
|------|------|
| ルール一覧取得 | 全アラートルールを一覧取得 |
| ルール作成 | マッチ条件、テンプレート、重要度を指定して作成（admin のみ） |
| ルール取得 | ID指定でアラートルールを取得 |
| ルール更新 | 指定フィールドのみ更新（admin のみ） |
| ルール削除 | アラートルールを削除（admin のみ） |
| ルール評価 | ログ作成時に有効ルールを自動評価し、条件一致でアラート生成 |

### 1.2 認可ルール

| 操作 | 権限 |
|------|------|
| 一覧取得 (`GET /`) | 認証済みユーザー |
| 個別取得 (`GET /{id}`) | 認証済みユーザー |
| 作成 (`POST /`) | admin のみ |
| 更新 (`PUT /{id}`) | admin のみ |
| 削除 (`DELETE /{id}`) | admin のみ |

---

## 2. エンドポイント一覧

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/alert-rules/` | アラートルール一覧 | 200 | 必要 |
| POST | `/api/alert-rules/` | アラートルール作成 | 201 / 422 | 必要（admin） |
| GET | `/api/alert-rules/{id}` | アラートルール取得 | 200 / 404 | 必要 |
| PUT | `/api/alert-rules/{id}` | アラートルール更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/alert-rules/{id}` | アラートルール削除 | 204 / 404 | 必要（admin） |

---

## 3. エンドポイント詳細

### 3.1 GET /api/alert-rules/

アラートルール一覧を取得する。ID昇順でソートされる。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `AlertRuleResponse[]`

**レスポンス例:**

```json
[
  {
    "id": 1,
    "name": "Error Alert",
    "condition": {"severity": "ERROR"},
    "alert_title_template": "{severity} in {system_name}",
    "alert_message_template": "{message}",
    "severity": "critical",
    "is_enabled": true,
    "created_at": "2026-02-12T10:00:00+09:00",
    "updated_at": "2026-02-12T10:00:00+09:00"
  }
]
```

### 3.2 POST /api/alert-rules/

アラートルールを作成する。

- **権限**: admin のみ（非admin は `403 Forbidden`）
- **リクエストボディ**: `AlertRuleCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | ルール名（最大200文字） |
| condition | object | Yes | - | マッチ条件（JSON、詳細は後述） |
| alert_title_template | string | Yes | - | タイトルテンプレート（最大500文字） |
| alert_message_template | string | No | null | メッセージテンプレート |
| severity | string | No | "warning" | 生成アラートの重要度（`info` / `warning` / `critical`） |
| is_enabled | boolean | No | true | ルール有効/無効 |

- **レスポンス**: `201 Created` - `AlertRuleResponse`
- **エラー**:
  - `403 Forbidden` - admin 以外のユーザー
  - `422 Unprocessable Entity` - バリデーションエラー（condition/severity）

**リクエスト例:**

```json
{
  "name": "Critical Error Alert",
  "condition": {
    "severity": {"$in": ["ERROR", "CRITICAL"]},
    "system_name": "production"
  },
  "alert_title_template": "{severity} in {system_name}",
  "alert_message_template": "Log message: {message}",
  "severity": "critical",
  "is_enabled": true
}
```

### 3.3 GET /api/alert-rules/{id}

指定IDのアラートルールを取得する。

- **権限**: 認証済みユーザー
- **パスパラメータ**: `id` (integer) - ルールID
- **レスポンス**: `200 OK` - `AlertRuleResponse`
- **エラー**: `404 Not Found` - ルール不存在

### 3.4 PUT /api/alert-rules/{id}

アラートルールを更新する。指定されたフィールドのみ更新される（`exclude_unset=True`）。

- **権限**: admin のみ（非admin は `403 Forbidden`）
- **パスパラメータ**: `id` (integer) - ルールID
- **リクエストボディ**: `AlertRuleUpdate`（全フィールド任意）

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| name | string | No | ルール名 |
| condition | object | No | マッチ条件 |
| alert_title_template | string | No | タイトルテンプレート |
| alert_message_template | string | No | メッセージテンプレート |
| severity | string | No | 重要度（`info` / `warning` / `critical`） |
| is_enabled | boolean | No | 有効/無効切り替え |

- **レスポンス**: `200 OK` - `AlertRuleResponse`
- **エラー**:
  - `403 Forbidden` - admin 以外のユーザー
  - `404 Not Found` - ルール不存在
  - `422 Unprocessable Entity` - バリデーションエラー

**有効/無効切り替えの例:**

```json
{
  "is_enabled": false
}
```

### 3.5 DELETE /api/alert-rules/{id}

アラートルールを削除する。ルールを参照しているアラートの `rule_id` は SET NULL となる。

- **権限**: admin のみ（非admin は `403 Forbidden`）
- **パスパラメータ**: `id` (integer) - ルールID
- **レスポンス**: `204 No Content`
- **エラー**:
  - `403 Forbidden` - admin 以外のユーザー
  - `404 Not Found` - ルール不存在

---

## 4. スキーマ

### 4.1 AlertRuleCreate

```python
class AlertRuleCreate(BaseModel):
    name: str
    condition: dict
    alert_title_template: str
    alert_message_template: Optional[str] = None
    severity: Literal["info", "warning", "critical"] = "warning"
    is_enabled: bool = True
```

### 4.2 AlertRuleUpdate

```python
class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[dict] = None
    alert_title_template: Optional[str] = None
    alert_message_template: Optional[str] = None
    severity: Optional[Literal["info", "warning", "critical"]] = None
    is_enabled: Optional[bool] = None
```

### 4.3 AlertRuleResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ルールID |
| name | string | ルール名 |
| condition | object | マッチ条件（JSON） |
| alert_title_template | string | タイトルテンプレート |
| alert_message_template | string \| null | メッセージテンプレート |
| severity | string | 生成アラートの重要度 |
| is_enabled | boolean | ルール有効/無効 |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

---

## 5. Condition（マッチ条件）仕様

### 5.1 概要

`condition` はログデータに対するマッチ条件をJSON形式で定義する。複数のフィールドを指定した場合は **AND** 条件で評価される。

### 5.2 マッチング対象フィールド

ログデータの以下のフィールドをマッチ対象として使用できる:

| フィールド | 型 | 説明 |
|------------|-----|------|
| system_name | string | システム名 |
| log_type | string | ログ種別 |
| severity | string | 重要度（`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`） |
| message | string | メッセージ |

> **注意**: ログの severity は大文字5段階（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）であり、アラートルールの severity（小文字3段階: `info`/`warning`/`critical`）とは体系が異なる。condition 内ではログ側の大文字値を指定すること。

### 5.3 演算子

#### 5.3.1 完全一致

フィールド値が指定値と完全に一致する場合にマッチ。

```json
{
  "severity": "ERROR"
}
```

#### 5.3.2 `$in` 演算子（リスト包含）

フィールド値が指定リストのいずれかと一致する場合にマッチ。

```json
{
  "severity": {"$in": ["ERROR", "CRITICAL"]}
}
```

#### 5.3.3 `$contains` 演算子（部分一致）

フィールド値（文字列化後）に指定文字列が含まれる場合にマッチ。

```json
{
  "message": {"$contains": "database"}
}
```

#### 5.3.4 複合条件（AND）

複数のフィールド条件を指定した場合、すべてがマッチする場合にのみアラートが生成される。

```json
{
  "severity": "ERROR",
  "system_name": "production",
  "message": {"$contains": "timeout"}
}
```

### 5.4 バリデーションルール

| ルール | エラー |
|--------|--------|
| condition が空 `{}` | 422 - `condition must not be empty` |
| 未知の演算子（`$in`/`$contains` 以外の `$` プレフィックス） | 422 - `Unknown operator(s) in condition: ...` |
| 値がリスト（配列）型 | 422 - `condition['field'] value must be a string or operator dict, not a list` |
| 演算子辞書が空 | 422 - `condition['field'] operator dict must not be empty` |

### 5.5 マッチングロジック

1. condition 内の各フィールド/値ペアを順に評価
2. ログデータにフィールドが存在しない場合 → **不一致**
3. 値が辞書型の場合:
   - `$in` → ログ値がリスト内に存在するか判定
   - `$contains` → ログ値（文字列化後）に部分文字列が含まれるか判定
   - 未知の演算子 → **不一致**
4. 値が文字列/数値の場合 → 完全一致で判定
5. すべての条件がマッチした場合のみアラート生成（AND ロジック）

---

## 6. テンプレート変数

### 6.1 概要

`alert_title_template` と `alert_message_template` にはログデータのフィールドをテンプレート変数として埋め込むことができる。

### 6.2 構文

`{field_name}` 形式でログデータのフィールドを参照する。

```
{severity} alert from {system_name}
```

### 6.3 利用可能な変数

| 変数 | 説明 |
|------|------|
| `{system_name}` | システム名 |
| `{log_type}` | ログ種別 |
| `{severity}` | ログの重要度 |
| `{message}` | ログメッセージ |

### 6.4 変数展開の動作

- 内部的に `{variable}` 構文を `${variable}` に変換し、Python の `string.Template.safe_substitute()` で安全に展開する
- 存在しない変数はそのまま残る（エラーにならない）
- `None` 値は空文字列に変換される
- format string injection を防止するため `str.format_map()` は使用しない

### 6.5 テンプレート例

**タイトルテンプレート:**
```
{severity} in {system_name}
```
→ ログ `{"severity": "ERROR", "system_name": "prod-server"}` に対して `ERROR in prod-server`

**メッセージテンプレート:**
```
Log: {message}
```
→ ログ `{"message": "Disk full"}` に対して `Log: Disk full`

**`alert_message_template` 未指定時:**
ログの `message` フィールドがそのままアラートメッセージとなる。

---

## 7. Severity（重要度）仕様

### 7.1 アラートルールの severity

生成されるアラートの重要度を指定する。小文字3段階:

| 値 | 説明 |
|----|------|
| `info` | 情報 |
| `warning` | 警告（デフォルト） |
| `critical` | 致命的 |

### 7.2 バリデーション

- `Literal["info", "warning", "critical"]` で厳密に検証
- 大文字混在（`Warning`）→ 422
- 空文字 → 422
- 未知の値（`INVALID`）→ 422

### 7.3 ログ severity との関係

| | ログ（logs テーブル） | アラートルール/アラート |
|--|-----|------|
| 体系 | 大文字5段階 | 小文字3段階 |
| 値 | DEBUG, INFO, WARNING, ERROR, CRITICAL | info, warning, critical |
| 用途 | ログの重要度分類 | 生成アラートの重要度 |

condition 内でログの severity をマッチングする際はログ側の大文字値を使用する:

```json
{
  "condition": {"severity": {"$in": ["ERROR", "CRITICAL"]}},
  "severity": "critical"
}
```

---

## 8. ルール評価エンジン

### 8.1 評価フロー

```
POST /api/logs/ (ログ作成)
  ↓
log_service.create_log(db, data)
  ↓ ログをDBに保存後
alert_service.evaluate_rules_for_log(db, log_data)
  ↓
有効ルール (is_enabled=true) を全件取得
  ↓ 各ルールに対して
_matches_condition(rule.condition, log_data)
  ↓ マッチした場合
テンプレート変数展開 → AlertCreate → DB保存
  ↓
_broadcast_alert() → WebSocket (/ws/alerts) で全クライアントに通知
```

### 8.2 動作仕様

- ログ作成のたびに有効な全ルール（`is_enabled=true`）を評価する
- 無効化されたルール（`is_enabled=false`）は評価対象外
- 1つのログに対して複数のルールがマッチ可能 → それぞれのルールからアラートが生成される
- 自動生成されたアラートの `rule_id` にはルールIDが設定される
- アラートの `source` にはログの `system_name` が設定される

### 8.3 WebSocket 通知

アラート生成時に以下の形式で `/ws/alerts` に配信される:

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

---

## 9. データベース

### 9.1 alert_rules テーブル

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ルールID |
| name | String(200) | NOT NULL | ルール名 |
| condition | JSON | NOT NULL | マッチ条件 |
| alert_title_template | String(500) | NOT NULL | タイトルテンプレート |
| alert_message_template | Text | NULL許可 | メッセージテンプレート |
| severity | String(20) | NOT NULL, DEFAULT "warning" | 生成アラートの重要度 |
| is_enabled | Boolean | NOT NULL, DEFAULT true | ルール有効/無効 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

### 9.2 リレーション

- `alerts.rule_id` → `alert_rules.id` (FK, SET NULL)
  - ルール削除時、関連アラートの `rule_id` は NULL に設定される

---

## 10. フロントエンド

### 10.1 画面構成

アラートルール管理は **Alerts画面** (`/alerts`) の下部セクションに配置されている。

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/alerts.html` |
| JavaScript | `static/js/alerts.js` |

### 10.2 ルール一覧テーブル

| カラム | 内容 |
|--------|------|
| Name | ルール名 |
| Condition | JSON形式でコード表示 |
| Severity | 重要度バッジ（色分け: critical=赤, warning=黄, info=水色） |
| Status | Enabled（緑）/ Disabled（グレー）バッジ |
| Actions | Edit / Enable・Disable トグル / Delete ボタン |

### 10.3 ルール作成/編集モーダル

| フィールド | 入力タイプ | 説明 |
|------------|-----------|------|
| Rule Name | テキスト | ルール名 |
| Severity | セレクト | info / warning / critical |
| Condition (JSON) | テキストエリア | JSON形式の条件式 |
| Title Template | テキスト | アラートタイトルテンプレート |
| Message Template | テキストエリア | アラートメッセージテンプレート |
| Enabled | チェックボックス | ルール有効/無効 |

### 10.4 JavaScript API

| 関数 | 説明 |
|------|------|
| `loadRules()` | `GET /api/alert-rules/` でルール一覧を取得・描画 |
| `openRuleModal(rule)` | ルール作成/編集モーダルを開く（rule=null で新規） |
| `editRule(id)` | `GET /api/alert-rules/{id}` でルールを取得しモーダルを開く |
| `saveRule()` | ルール保存（ID有→PUT 更新、ID無→POST 作成） |
| `toggleRule(id, enabled)` | `PUT /api/alert-rules/{id}` で有効/無効を切り替え |
| `deleteRule(id)` | 確認ダイアログ後に `DELETE /api/alert-rules/{id}` |

---

## 11. 実装ファイル一覧

| レイヤー | ファイル | 説明 |
|---------|---------|------|
| ルーター | `app/routers/api_alert_rules.py` | HTTPエンドポイント定義（5エンドポイント、全 async） |
| サービス | `app/services/alert_service.py` | ルールCRUD + 評価エンジン + テンプレート展開 + WebSocket通知 |
| CRUD | `app/crud/alert.py` | DB操作（alert_rules + alerts 共用） |
| スキーマ | `app/schemas/alert.py` | Pydantic バリデーション（condition/severity 検証含む） |
| モデル | `app/models/alert.py` | SQLAlchemy ORM定義（AlertRule + Alert 共用） |
| テスト | `tests/test_alert_rules.py` | 29テストケース（7クラス） |
| フロントエンド | `static/js/alerts.js` | ルール一覧・作成・編集・削除のクライアント実装 |

---

## 12. テスト仕様

### 12.1 テスト構成

| テストクラス | テスト数 | 内容 |
|-------------|---------|------|
| TestAlertRuleCRUD | 7 | 基本CRUD操作 |
| TestAlertRuleSeverityValidation | 2 | severity バリデーション |
| TestAlertRuleConditionValidation | 5 | condition バリデーション |
| TestAlertRuleRBAC | 4 | 権限制御 |
| TestRuleEvaluation | 7 | 評価エンジン（ユニット） |
| TestRuleEvaluationIntegration | 4 | 評価エンジン（統合） |
| **合計** | **29** | |

### 12.2 テストケース一覧

#### CRUD テスト (TestAlertRuleCRUD)

| テストケース | 検証内容 |
|-------------|---------|
| test_create_rule | ルール作成（201 + AlertRuleResponse） |
| test_list_rules | ルール一覧取得 |
| test_get_rule | ID指定でルール取得 |
| test_get_rule_not_found | 存在しないIDで404 |
| test_update_rule | ルール名更新 |
| test_delete_rule | 削除後に取得で404 |
| test_toggle_rule | 有効/無効の切り替え |

#### Severity バリデーション テスト (TestAlertRuleSeverityValidation)

| テストケース | 検証内容 |
|-------------|---------|
| test_invalid_rule_severity_rejected | 不正な severity で422 |
| test_empty_rule_severity_rejected | 空文字 severity で422 |

#### Condition バリデーション テスト (TestAlertRuleConditionValidation)

| テストケース | 検証内容 |
|-------------|---------|
| test_empty_condition_rejected | 空の condition `{}` で422 |
| test_unknown_operator_rejected | 不正な演算子 `$unknown` で422 |
| test_list_value_rejected | リスト値 `[1, 2, 3]` で422 |
| test_valid_in_operator_accepted | `$in` 演算子が受け入れられる（201） |
| test_valid_contains_operator_accepted | `$contains` 演算子が受け入れられる（201） |

#### RBAC テスト (TestAlertRuleRBAC)

| テストケース | 検証内容 |
|-------------|---------|
| test_non_admin_can_read_rules | 非adminでルール一覧読み取り可（200） |
| test_non_admin_cannot_create_rule | 非adminでルール作成で403 |
| test_non_admin_cannot_update_rule | 非adminでルール更新で403 |
| test_non_admin_cannot_delete_rule | 非adminでルール削除で403 |

#### 評価エンジン ユニットテスト (TestRuleEvaluation)

| テストケース | 検証内容 |
|-------------|---------|
| test_exact_match | 完全一致条件のマッチ |
| test_no_match | 条件不一致 |
| test_in_operator | `$in` 演算子のマッチ（マッチ/不一致の両方） |
| test_contains_operator | `$contains` 演算子のマッチ（マッチ/不一致の両方） |
| test_multiple_conditions_and | 複数条件のAND評価 |
| test_missing_field_no_match | ログにフィールド欠落時の不一致 |
| test_unknown_operator_no_match | 不正な演算子 → 不一致（安全なフォールバック） |

#### 評価エンジン 統合テスト (TestRuleEvaluationIntegration)

| テストケース | 検証内容 |
|-------------|---------|
| test_log_triggers_alert | ログ → ルール評価 → アラート自動生成の統合フロー |
| test_disabled_rule_no_alert | 無効ルールはアラートを生成しない |
| test_template_variables | テンプレート変数の正しい展開確認 |
| test_multiple_rules_match_same_log | 複数ルールが同一ログにマッチ → 複数アラート生成 |

### 12.3 テスト実行

```bash
pytest tests/test_alert_rules.py -q
```

---

## 13. 設計判断・注意事項

### 13.1 セキュリティ

- テンプレート展開に `string.Template.safe_substitute()` を使用し、format string injection を防止
- condition のバリデーションで不正な演算子やデータ型を事前に拒否
- RBAC による admin 限定のCUD操作

### 13.2 パフォーマンス

- ルール評価はログ作成のたびに実行されるため、有効ルール数が増加すると影響する可能性がある
- `get_enabled_alert_rules()` は `is_enabled=True` のルールのみ取得し、無効ルールは評価対象外

### 13.3 ログ severity とアラート severity の分離

ログの severity（大文字5段階）とアラートの severity（小文字3段階）は意図的に分離されている。これにより:
- ログの重要度分類（DEBUG～CRITICAL）は外部システムとの互換性を維持
- アラートの重要度（info/warning/critical）はUI表示・運用フローに最適化
