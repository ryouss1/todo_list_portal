# Daily Report 機能仕様書

> 日報管理機能の完全な仕様。タスク分類・作業時間・作業内容の記録、Task Done 時の自動生成、Business Summary との連携を含む。

---

## 1. 概要

### 1.1 背景

ユーザーの日々の作業内容を記録・共有するための日報機能。
タスク分類ごとに作業内容と作業時間を記録し、チーム全体の作業状況を可視化する。
Tasks 画面で Task を Done にした際に自動生成する機能も備える。

### 1.2 目的

- 日付・タスク分類・タスク名・作業時間・作業内容を軸とした日報の CRUD
- 成果（Achievements）、課題（Issues）、次の計画（Next Plan）、備考（Remarks）の任意記入
- 全ユーザーの日報を閲覧可能（編集・削除はオーナーのみ）
- Task Done 時の自動日報生成（`report` フラグ連動）
- Business Summary 機能へのデータ提供

### 1.3 基本フロー

```
手動作成:  ユーザー → [New Report] → モーダル入力 → DailyReport 作成
自動生成:  Task Done → report=true → DailyReport 自動作成（タイトル・時間・カテゴリをコピー）
閲覧:     My Reports / All Reports タブ → 日付フィルター → テーブル一覧 → 詳細画面
```

- 同一ユーザー・同一日付で複数レポートの作成が可能（UNIQUE 制約なし）
- 閲覧は全認証ユーザーに公開、編集・削除はオーナーのみ

---

## 2. データモデル

### 2.1 daily_reports テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | レポートID |
| user_id | INTEGER | FK → users.id, NOT NULL | 作成者ユーザーID |
| report_date | DATE | NOT NULL | レポート対象日 |
| category_id | INTEGER | FK → task_categories.id, NOT NULL | タスク分類ID |
| task_name | VARCHAR(200) | NOT NULL | タスク名 |
| time_minutes | INTEGER | NOT NULL, DEFAULT 0 | 作業時間（分） |
| work_content | TEXT | NOT NULL | 作業内容 |
| achievements | TEXT | NULL 可 | 成果 |
| issues | TEXT | NULL 可 | 課題 |
| next_plan | TEXT | NULL 可 | 次の計画 |
| remarks | TEXT | NULL 可 | 備考 |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 更新日時 |

### 2.2 task_categories テーブルとの連携

`category_id` は `task_categories.id` への FK。タスク分類マスタは以下がシードされている:

| id | name |
|----|------|
| 1 | 開発 |
| 2 | 設計 |
| 3 | テスト |
| 4 | ミーティング |
| 5 | レビュー |
| 6 | 調査 |
| 7 | その他 |

Task Done による自動生成時は `task.category_id` をコピーし、未設定の場合は `DEFAULT_CATEGORY_ID = 7`（その他）を使用。

### 2.3 UNIQUE 制約の経緯

- 初期: `uq_user_report_date`（user_id + report_date で 1 日 1 件制限）
- 現在: **UNIQUE 制約削除済み**（migration `e3a82a9fcd2f`）。同一ユーザー・同一日付で複数レポート作成可能

---

## 3. API エンドポイント

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）

### 3.1 一覧取得

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/reports/` | 自分のレポート一覧 | `200` DailyReportResponse[] |
| GET | `/api/reports/all` | 全ユーザーのレポート一覧 | `200` DailyReportResponse[] |

**クエリパラメータ（共通）**:
- `report_date` (任意): 指定日のレポートのみ取得。省略時は全日付

ソート順: `report_date DESC`

### 3.2 CRUD

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/reports/` | レポート作成 | `201` DailyReportResponse |
| GET | `/api/reports/{id}` | レポート取得（全ユーザー閲覧可） | `200` DailyReportResponse / `404` |
| PUT | `/api/reports/{id}` | レポート更新（オーナーのみ） | `200` DailyReportResponse / `404` |
| DELETE | `/api/reports/{id}` | レポート削除（オーナーのみ） | `204` / `404` |

### 3.3 権限チェック

| 操作 | チェック関数 | 説明 |
|------|------------|------|
| GET（単一） | `get_report()` | 存在チェックのみ。全認証ユーザーが閲覧可能 |
| PUT / DELETE | `get_own_report()` | `report.user_id == user_id` を確認。不一致時は `404`（他ユーザーの存在を隠す） |

---

## 4. スキーマ

### DailyReportCreate
```json
{
  "report_date": "2026-02-10 (必須)",
  "category_id": "int (必須)",
  "task_name": "string (必須)",
  "time_minutes": "int (デフォルト 0)",
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

- `report_date` は更新不可（Update スキーマに含まれない）
- `exclude_unset=True` で未指定フィールドは変更なし

### DailyReportResponse
```json
{
  "id": 1,
  "user_id": 1,
  "report_date": "2026-02-10",
  "category_id": 7,
  "task_name": "Feature implementation",
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

---

## 5. Task Done 自動生成

Tasks 画面で Task を Done（単一 / Batch-Done）した際、`task.report == true` の場合に DailyReport を自動生成する。

### 5.1 自動生成の処理フロー

```
Task Done → report=true? → YES → DailyReport 自動作成
                          → NO  → スキップ
```

### 5.2 フィールドマッピング

| DailyReport フィールド | ソース | 説明 |
|----------------------|--------|------|
| `report_date` | `date.today()` (単一 Done) / `task_date` (Batch-Done) | Batch-Done ではタスクの `updated_at` ローカル日付を使用 |
| `category_id` | `task.category_id` or `DEFAULT_CATEGORY_ID(7)` | タスクにカテゴリ未設定時は「その他」 |
| `task_name` | `task.title` | タスクタイトルをそのままコピー |
| `time_minutes` | `task.total_seconds // 60` | 秒を分に変換（切り捨て） |
| `work_content` | 下記参照 | タイトル + 時間 + 説明の結合 |
| `achievements` | ― | 未設定（`null`） |
| `issues` | ― | 未設定（`null`） |
| `next_plan` | ― | 未設定（`null`） |
| `remarks` | ― | 未設定（`null`） |

### 5.3 work_content の自動生成フォーマット

```
{task.title} ({hours}h {mins}m)
{task.description}
```

- 作業時間が 0 の場合は時間部分を省略
- `task.description` が未設定の場合はタイトル行のみ

### 5.4 Batch-Done の場合

- `report_date` は `task_date`（タスクの `updated_at` のローカル日付）を使用（`date.today()` ではない）
- DailyReport は flush のみ（commit は全タスク処理後にアトミック実行）

---

## 6. フロントエンド

### 6.1 一覧画面（`/reports`）

- テンプレート: `templates/reports.html`
- JavaScript: `static/js/reports.js?v=5`
- ナビバー: `bi-journal-text` アイコンで表示

```
Daily Reports ページ
├── [New Report] ボタン → モーダル
├── タブ
│   ├── [My Reports] タブ ← デフォルト
│   └── [All Reports] タブ（投稿者列が追加表示）
├── 日付フィルター（date input + 検索/クリアボタン）
└── テーブル一覧
    └── 日付 / 分類 / タスク名 / 時間 / 作業内容 / [投稿者]
```

### 6.2 一覧テーブル

| 列 | 説明 |
|------|------|
| 日付 | `report_date`（太字） |
| 分類 | `category_id` をクライアントサイドでカテゴリ名に解決（`badge bg-info`） |
| タスク名 | `task_name`（`escapeHtml` でサニタイズ） |
| 時間 | `time_minutes` を `Xh Ym` 形式で表示（`badge bg-light`） |
| 作業内容 | `work_content` の先頭 80 文字 + 省略記号 |
| 投稿者 | `user_id` を `display_name` で解決（All Reports タブのみ表示） |

- 行クリックで詳細画面（`/reports/{id}`）に遷移
- 日付フィルターのデフォルト値は `today`（フィルタークリア時も today にリセット）
- Enter キーで日付検索実行

### 6.3 新規作成モーダル

| フィールド | 入力タイプ | 必須 | 説明 |
|-----------|----------|------|------|
| Date | `date` | YES | デフォルト: today |
| タスク分類 | `select` | YES | カテゴリ API から動的生成 |
| 時間（分） | `number` | YES | デフォルト: 0、min=0 |
| タスク名 | `text` | YES | |
| Work Content | `textarea` | YES | 3 行 |
| Achievements | `textarea` | NO | 2 行 |
| Issues | `textarea` | NO | 2 行 |
| Next Plan | `textarea` | NO | 2 行 |
| Remarks | `textarea` | NO | 2 行 |

フロント側バリデーション: Date, タスク分類, タスク名, Work Content が未入力の場合は `alert()` で警告。

### 6.4 詳細画面（`/reports/{id}`）

- テンプレート: `templates/report_detail.html`
- JavaScript: `static/js/report_detail.js?v=4`
- `REPORT_ID` はテンプレートからインラインスクリプトで注入

```
Report Detail ページ
├── ヘッダー: [Back] ボタン + [Edit] [Delete] ボタン（オーナーのみ表示）
├── メインカード
│   ├── report_date + 投稿者名 + created_at
│   └── タスク分類バッジ + タスク名 + 時間バッジ
├── Work Content カード（常時表示）
├── Achievements カード（値がある場合のみ表示、緑枠）
├── Issues カード（値がある場合のみ表示、赤枠）
├── Next Plan カード（値がある場合のみ表示、青枠）
└── Remarks カード（値がある場合のみ表示、グレー枠）
```

### 6.5 編集モーダル（詳細画面内）

- `report.user_id === currentUserId` の場合のみ Edit / Delete ボタンを表示
- 編集モーダルはカード形式の UI（色分け: info=Task Info, dark=Work Content, success=Achievements, danger=Issues, primary=Next Plan, secondary=Remarks）
- Delete は `confirm()` ダイアログ後に実行、削除後は `/reports` にリダイレクト

### 6.6 初期化・データ読み込み

```javascript
// 一覧画面: 並列で 2 API を呼び出し
await Promise.all([loadUsers(), loadCategories()]);

// 詳細画面: 並列で 4 API を呼び出し
const [r, me, users, categories] = await Promise.all([
    api.get(`/api/reports/${REPORT_ID}`),
    api.get('/api/auth/me'),
    api.get('/api/users/'),
    api.get('/api/task-categories/')
]);
```

---

## 7. ビジネスルール

### 7.1 可視性・権限

| 操作 | 権限 |
|------|------|
| 一覧閲覧（自分） | 全認証ユーザー |
| 一覧閲覧（全体） | 全認証ユーザー |
| 単一取得 | 全認証ユーザー |
| 作成 | 全認証ユーザー（自分の日報のみ） |
| 編集 | **オーナーのみ**（`report.user_id == user_id`） |
| 削除 | **オーナーのみ**（`report.user_id == user_id`） |

- 他ユーザーの日報を編集・削除しようとした場合は `404`（存在の隠蔽）

### 7.2 日付・重複

| ルール | 説明 |
|--------|------|
| 同一日複数レポート | 同一ユーザー・同一日付で複数レポートの作成が可能 |
| 日付変更不可 | `report_date` は作成後の更新不可（Update スキーマに含まれない） |
| 日付フィルターデフォルト | フロント側で today を初期値とする |

### 7.3 自動生成

| ルール | 説明 |
|--------|------|
| report フラグ | Task の `report` フラグが `true` の場合のみ自動生成 |
| カテゴリフォールバック | タスクの `category_id` が未設定の場合は `DEFAULT_CATEGORY_ID = 7`（その他） |
| 時間の切り捨て | `total_seconds // 60` で分に変換（端数切り捨て） |
| Batch-Done の日付 | `task_date`（タスクの `updated_at` ローカル日付）を使用 |
| 自動生成内容 | `work_content` のみ自動設定。achievements / issues / next_plan / remarks は `null` |

### 7.4 カテゴリ

| ルール | 説明 |
|--------|------|
| FK 制約 | `category_id` は `task_categories.id` への外部キー |
| クライアント側解決 | カテゴリ名は `GET /api/task-categories/` で取得し、JS 側で `categoryMap` にキャッシュ |

---

## 8. Business Summary 連携

`summary_service.py` が DailyReport データを集計して Business Summary を生成する。

| 集計項目 | 説明 |
|---------|------|
| `total_reports` | 期間内の全レポート数 |
| `user_report_statuses` | ユーザーごとのレポート数 + 今日のレポート有無 |
| `report_trends` | 日付ごとのレポート数 + カテゴリ別内訳（`CategoryTrend`） |
| `category_trends` | カテゴリごとの合計レポート数 + 合計時間（分） |
| `recent_reports` | 直近 10 件のレポートサマリー |
| `issues` | レポートの `issues` フィールドを日付・ユーザー名付きで収集 |

---

## 9. ファイル構成

### 9.1 新規作成（8 ファイル）

| ファイル | 内容 |
|---------|------|
| `app/models/daily_report.py` | DailyReport モデル |
| `app/schemas/daily_report.py` | リクエスト/レスポンススキーマ |
| `app/crud/daily_report.py` | CRUD 操作（一覧、日付範囲、作成、更新、削除） |
| `app/services/daily_report_service.py` | ビジネスロジック（権限チェック・CRUD） |
| `app/routers/api_reports.py` | API エンドポイント（6 ルート） |
| `templates/reports.html` | 一覧画面テンプレート |
| `templates/report_detail.html` | 詳細画面テンプレート |
| `static/js/reports.js` | 一覧画面 JS |

### 9.2 追加作成（1 ファイル）

| ファイル | 内容 |
|---------|------|
| `static/js/report_detail.js` | 詳細画面 JS（閲覧・編集・削除） |

### 9.3 変更

| ファイル | 変更内容 |
|---------|---------|
| `app/services/task_service.py` | `done_task()` / `batch_done()` に自動日報生成ロジック追加 |
| `app/services/summary_service.py` | DailyReport データ集計ロジック |
| `main.py` | router 登録追加 |
| `app/routers/pages.py` | `/reports`, `/reports/{id}` ページルート追加 |
| `templates/base.html` | Reports ナビリンク追加 |

---

## 10. テスト

`tests/test_reports.py` に 17 テストケース（2 クラス）。

### TestReportAPI — CRUD テスト（13 件）

- 空一覧の取得確認
- 全フィールド指定でのレポート作成（category_id, task_name, time_minutes 含む）
- 最小フィールド（必須のみ）でのレポート作成確認（achievements / issues / time_minutes がデフォルト値）
- 必須フィールド不足でのバリデーションエラー（`422`）: report_date のみ
- `category_id` 不足でのバリデーションエラー（`422`）
- `task_name` 不足でのバリデーションエラー（`422`）
- `time_minutes` 指定での作成確認
- 同一日付での複数レポート作成確認
- 単一レポート取得確認
- レポート更新確認（`work_content` 変更）
- カテゴリ + タスク名の更新確認
- レポート削除確認（削除後の `404` 確認）
- 全ユーザーレポート一覧の取得確認

### TestReportAuthorization — 認可テスト（4 件）

- 他ユーザーのレポートが閲覧可能であることの確認
- 他ユーザーのレポートを更新できないことの確認（`404`）
- 他ユーザーのレポートを削除できないことの確認（`404`）
- 全一覧に他ユーザーのレポートが含まれることの確認

---

## 11. ダッシュボード連携

`templates/index.html` のダッシュボードに Reports サマリーが表示される。

- `GET /api/reports/` を取得
- `"{count} reports"` 形式で自分のレポート数を表示

---

## 12. マイグレーション

| Revision | 説明 |
|---------|------|
| `c3790ffa7e38` | `daily_reports` テーブル作成（初期: `uq_user_report_date` UNIQUE 制約あり） |
| `709a8464bb48` | `category_id`, `task_name`, `time_minutes` カラム追加 + `task_categories` テーブル作成 |
| `e3a82a9fcd2f` | `uq_user_report_date` UNIQUE 制約を削除（同一日複数レポート対応） |
