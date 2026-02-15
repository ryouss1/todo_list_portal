# Daily Report 機能仕様書

> 日報機能の完全な仕様。タスク分類・タスク名・作業時間の管理、一覧・詳細表示、Task 連携を含む。

---

## 1. 概要

Daily Report はユーザーの日々の作業内容を記録・共有する機能。
各レポートにはタスク分類（マスタから選択）、タスク名、作業時間（分）、作業内容を必須として記録し、
成果・課題・次の計画・備考を任意で記入できる。

全認証ユーザーが全員のレポートを閲覧可能、編集・削除は作成者本人のみ。

---

## 2. データモデル

### 2.1 task_categories テーブル（マスタ）

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | カテゴリID |
| name | VARCHAR(100) | NOT NULL | カテゴリ名 |

**シードデータ（初期値）**:

| ID | name |
|----|------|
| 1 | 開発 |
| 2 | 設計 |
| 3 | テスト |
| 4 | ミーティング |
| 5 | レビュー |
| 6 | 調査 |
| 7 | その他 |

### 2.2 daily_reports テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | レポートID |
| user_id | INTEGER | FK → users.id, NOT NULL | 作成ユーザー |
| report_date | DATE | NOT NULL | レポート日付 |
| category_id | INTEGER | FK → task_categories.id, NOT NULL | タスク分類 |
| task_name | VARCHAR(200) | NOT NULL | タスク名 |
| time_minutes | INTEGER | NOT NULL, DEFAULT 0 | 作業時間（分） |
| work_content | TEXT | NOT NULL | 作業内容 |
| achievements | TEXT | NULL 可 | 成果 |
| issues | TEXT | NULL 可 | 課題 |
| next_plan | TEXT | NULL 可 | 次の計画 |
| remarks | TEXT | NULL 可 | 備考 |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 更新日時 |

---

## 3. API エンドポイント

### 3.1 Daily Report API

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/reports/` | 自分のレポート一覧 | `200` DailyReportResponse[] |
| GET | `/api/reports/all` | 全員のレポート一覧 | `200` DailyReportResponse[] |
| POST | `/api/reports/` | レポート作成 | `201` DailyReportResponse |
| GET | `/api/reports/{id}` | レポート詳細取得 | `200` DailyReportResponse / `404` |
| PUT | `/api/reports/{id}` | レポート更新（本人のみ） | `200` DailyReportResponse / `404` |
| DELETE | `/api/reports/{id}` | レポート削除（本人のみ） | `204` / `404` |

**日付フィルタ**: `GET /api/reports/` と `GET /api/reports/all` は `?report_date=YYYY-MM-DD` クエリパラメータで日付絞り込み可能。

### 3.2 TaskCategory API

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| GET | `/api/task-categories/` | 認証ユーザー | カテゴリ一覧 |
| POST | `/api/task-categories/` | Admin のみ | カテゴリ作成 |
| PUT | `/api/task-categories/{id}` | Admin のみ | カテゴリ更新 |
| DELETE | `/api/task-categories/{id}` | Admin のみ | カテゴリ削除 |

---

## 4. スキーマ

### DailyReportCreate
```json
{
  "report_date": "YYYY-MM-DD (必須)",
  "category_id": "int (必須)",
  "task_name": "string (必須)",
  "time_minutes": 0,
  "work_content": "string (必須)",
  "achievements": "string (任意)",
  "issues": "string (任意)",
  "next_plan": "string (任意)",
  "remarks": "string (任意)"
}
```

### DailyReportUpdate
```json
{
  "category_id": "int (任意)",
  "task_name": "string (任意)",
  "time_minutes": "int (任意)",
  "work_content": "string (任意)",
  "achievements": "string (任意)",
  "issues": "string (任意)",
  "next_plan": "string (任意)",
  "remarks": "string (任意)"
}
```

### DailyReportResponse
```json
{
  "id": 1,
  "user_id": 1,
  "report_date": "2025-01-15",
  "category_id": 1,
  "task_name": "API設計",
  "time_minutes": 120,
  "work_content": "string",
  "achievements": "string|null",
  "issues": "string|null",
  "next_plan": "string|null",
  "remarks": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime|null"
}
```

### TaskCategoryCreate / TaskCategoryResponse
```json
// Create
{ "name": "string (必須)" }

// Response
{ "id": 1, "name": "開発" }
```

---

## 5. フロントエンド

### 5.1 一覧画面（`/reports`）

- テンプレート: `templates/reports.html`
- JavaScript: `static/js/reports.js`

#### タブ構成

| タブ | 説明 | デフォルト日付 |
|------|------|---------------|
| My Reports | 自分のレポート | 当日 |
| All Reports | 全員のレポート | 当日 |

#### テーブル表示

| カラム | 説明 |
|--------|------|
| 日付 | レポート日付（太字） |
| 分類 | カテゴリ名（info バッジ） |
| タスク名 | タスク名称 |
| 時間 | 作業時間（Xh Ym 形式、light バッジ） |
| 作業内容 | 先頭 80 文字 + 省略記号 |
| 投稿者 | All Reports タブのみ表示 |

各行クリックで詳細画面（`/reports/{id}`）へ遷移。

#### 日付検索

- 日付入力フィールド + 検索ボタン + クリアボタン
- クリアボタン: 当日にリセット
- Enter キーで検索実行
- タブ切り替え時: 当日にリセット

#### 新規作成モーダル

- 日付（デフォルト: 当日）
- タスク分類（ドロップダウン、必須）
- 時間（分単位、デフォルト: 0）
- タスク名（テキスト、必須）
- 作業内容（テキストエリア、必須）
- 成果・課題・次の計画・備考（テキストエリア、任意）

### 5.2 詳細画面（`/reports/{id}`）

- テンプレート: `templates/report_detail.html`
- JavaScript: `static/js/report_detail.js`

#### 表示構成

- ヘッダーカード: 日付、投稿者、作成日時、タスク情報（分類・タスク名・時間）
- 色分けされたセクションカード:
  - **Work Content**: ダーク枠（常に表示）
  - **Achievements**: グリーン枠（値がある場合のみ）
  - **Issues**: レッド枠（値がある場合のみ）
  - **Next Plan**: ブルー枠（値がある場合のみ）
  - **Remarks**: グレー枠（値がある場合のみ）

#### 操作ボタン（本人のみ表示）

- Edit: 編集モーダルを開く
- Delete: 確認後に削除、一覧画面へ遷移

#### 編集モーダル

色分けされたカード形式のフォーム:
- Task Info（info 枠）: タスク分類・タスク名・時間
- Work Content（dark 枠）: 作業内容
- Achievements（success 枠）: 成果
- Issues（danger 枠）: 課題
- Next Plan（primary 枠）: 次の計画
- Remarks（secondary 枠）: 備考

---

## 6. Task 機能連携

Task の Done / Batch-Done で `report=true` の場合、DailyReport が自動作成される。

| フィールド | 値 |
|-----------|-----|
| report_date | Done: 当日、Batch-Done: タスクの `updated_at` 日付 |
| category_id | `7`（その他） |
| task_name | タスクのタイトル |
| time_minutes | `total_seconds // 60` |
| work_content | `"{title} ({Xh Ym})\n{description}"` |

---

## 7. ビジネスルール

| ルール | 説明 |
|--------|------|
| 閲覧権限 | 全認証ユーザーが全レポートを閲覧可能 |
| 編集権限 | 作成者本人のみ編集・削除可能（他ユーザーは 404） |
| 同一日複数レポート | 同一ユーザー・同一日付で複数レポート作成可能 |
| カテゴリ管理 | Admin のみ作成・更新・削除可能、全ユーザー閲覧可能 |
| デフォルト表示 | 両タブとも当日のレポートを表示 |
| カテゴリ名解決 | JS クライアント側でカテゴリリストを取得して名前マッピング |

---

## 8. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/task_category.py` | TaskCategory モデル |
| `app/models/daily_report.py` | DailyReport モデル |
| `app/schemas/task_category.py` | カテゴリスキーマ |
| `app/schemas/daily_report.py` | レポートスキーマ |
| `app/crud/task_category.py` | カテゴリ CRUD |
| `app/crud/daily_report.py` | レポート CRUD |
| `app/services/task_category_service.py` | カテゴリサービス |
| `app/services/daily_report_service.py` | レポートサービス |
| `app/routers/api_task_categories.py` | カテゴリ API |
| `app/routers/api_reports.py` | レポート API |
| `templates/reports.html` | 一覧画面テンプレート |
| `templates/report_detail.html` | 詳細画面テンプレート |
| `static/js/reports.js` | 一覧画面 JS |
| `static/js/report_detail.js` | 詳細画面 JS |
| `tests/test_reports.py` | レポートテスト（17 件） |
| `tests/test_task_categories.py` | カテゴリテスト（11 件） |

---

## 9. テスト

### test_reports.py（17 件）

- CRUD 基本操作（一覧、作成、取得、更新、削除）
- 日付フィルタ（My Reports、All Reports）
- 権限テスト（他ユーザーの更新・削除拒否）
- バリデーション（category_id 未指定 → 422、task_name 未指定 → 422）
- 時間フィールドの保存・更新確認
- カテゴリ変更テスト

### test_task_categories.py（11 件）

- カテゴリ CRUD（一覧、作成、取得、更新、削除）
- 権限テスト（一般ユーザーは作成・更新・削除不可 → 403）
