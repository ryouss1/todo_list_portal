# Business Summary 機能仕様書

> 日報データを集約し、日次・週次・月次のビジネスサマリーを表示する読み取り専用の分析機能。ユーザー別レポート状況、レポート推移、分類別傾向、課題一覧、最近の日報を一画面で確認できる。

---

## 1. 概要

### 1.1 背景

DailyReport のデータを基に、チーム全体の作業状況を可視化する分析画面。
指定期間（daily / weekly / monthly）の集約情報を生成し、ナビゲーションボタンで期間を切り替えながら傾向を確認できる。

### 1.2 目的

- ユーザー別のレポート提出状況と分類別作業時間の可視化
- 日別レポート推移のトレンド表示（分類別積み上げバー）
- 分類別傾向の集計（レポート件数・合計作業時間）
- 課題（issues）の一覧表示
- 最近の日報プレビュー（詳細へのリンク付き）

### 1.3 特性

- **読み取り専用**: データの作成・更新・削除は行わない
- **専用テーブルなし**: `daily_reports`, `users`, `task_categories` を参照するのみ
- **全認証ユーザーがアクセス可能**: 権限制限なし

---

## 2. データソース

### 2.1 参照テーブル

| テーブル | 用途 |
|---------|------|
| `daily_reports` | 集約対象データ（report_date, user_id, category_id, time_minutes, work_content, issues） |
| `users` | ユーザー名の解決 |
| `task_categories` | 分類名の解決、カラーパレット割り当て |

### 2.2 使用フィールド

| フィールド | 用途 |
|-----------|------|
| `report_date` | 期間フィルタ、日別トレンド集計 |
| `user_id` | ユーザー別レポート数集計 |
| `category_id` | 分類別傾向集計 |
| `time_minutes` | 分類別作業時間集計 |
| `work_content` | 最近の日報プレビュー（先頭 100 文字） |
| `issues` | 課題一覧抽出 |

---

## 3. API エンドポイント

認証: 必要（全認証ユーザー）

### 3.1 GET /api/summary/

ビジネスサマリーを取得する。

**クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|----------|------|
| `period` | string | `"weekly"` | 集約期間。`daily`, `weekly`, `monthly`。それ以外は `422` |
| `ref_date` | date (YYYY-MM-DD) | 今日 | 基準日。この日を含む期間を集計範囲とする |

**バリデーション**: `period` パラメータは正規表現 `^(daily|weekly|monthly)$` で制約（FastAPI `Query(pattern=...)`)

---

## 4. スキーマ

### BusinessSummaryResponse

```json
{
  "period_start": "2026-02-09",
  "period_end": "2026-02-15",
  "period": "weekly",
  "total_reports": 12,
  "categories": [...],
  "user_report_statuses": [...],
  "report_trends": [...],
  "category_trends": [...],
  "recent_reports": [...],
  "issues": [...]
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| `period_start` | date | 集計期間の開始日 |
| `period_end` | date | 集計期間の終了日 |
| `period` | string | `"daily"`, `"weekly"`, or `"monthly"` |
| `total_reports` | int | 期間内の総レポート数 |
| `categories` | List[CategoryInfo] | 全タスク分類リスト（ID 昇順、フロント用カラーマップ生成） |
| `user_report_statuses` | List[UserReportStatus] | ユーザー別レポート状況 |
| `report_trends` | List[ReportTrend] | 日別レポート数推移 |
| `category_trends` | List[CategoryTrend] | 分類別傾向（作業時間降順） |
| `recent_reports` | List[RecentReportSummary] | 最近の日報（最大 10 件） |
| `issues` | List[string] | 課題一覧（日付・ユーザー名付き） |

### サブスキーマ

**CategoryInfo**

| フィールド | 型 | 説明 |
|-----------|------|------|
| `id` | int | 分類 ID |
| `name` | string | 分類名 |

**CategoryCount**（`UserReportStatus` / `ReportTrend` 内の分類別内訳）

| フィールド | 型 | 説明 |
|-----------|------|------|
| `category_id` | int | 分類 ID |
| `category_name` | string | 分類名 |
| `count` | int | 当該分類のレポート数 |
| `total_minutes` | int | 当該分類の合計作業時間（分）。デフォルト 0 |

**UserReportStatus**

| フィールド | 型 | 説明 |
|-----------|------|------|
| `user_id` | int | ユーザー ID |
| `display_name` | string | 表示名 |
| `report_count` | int | 期間内のレポート数 |
| `has_report_today` | bool | 今日のレポートがあるか |
| `category_breakdown` | List[CategoryCount] | 分類別レポート数・作業時間（全カテゴリ、0 件含む） |

**ReportTrend**

| フィールド | 型 | 説明 |
|-----------|------|------|
| `date` | date | 日付 |
| `count` | int | その日のレポート数 |
| `category_breakdown` | List[CategoryCount] | 分類別レポート数（0 件除外） |

**CategoryTrend**

| フィールド | 型 | 説明 |
|-----------|------|------|
| `category_id` | int | 分類 ID |
| `category_name` | string | 分類名（未解決時は `"Unknown"`） |
| `report_count` | int | 当該分類のレポート数 |
| `total_minutes` | int | 当該分類の合計作業時間（分） |

**RecentReportSummary**

| フィールド | 型 | 説明 |
|-----------|------|------|
| `id` | int | 日報 ID |
| `user_id` | int | ユーザー ID |
| `display_name` | string | 表示名 |
| `report_date` | date | レポート日付 |
| `work_content_preview` | string | 作業内容の先頭 100 文字 |

---

## 5. 期間算出ロジック

### 5.1 Daily（日次）

基準日 `ref_date` の **1 日のみ** を集計範囲とする。

```
period_start = ref_date
period_end   = ref_date
```

例: `ref_date = 2026-02-10` → `2026-02-10 〜 2026-02-10`

### 5.2 Weekly（週次）

基準日 `ref_date` を含む **月曜〜日曜** の 1 週間を算出する。

```
period_start = ref_date - ref_date.weekday()  # 月曜日
period_end   = period_start + 6 days           # 日曜日
```

例: `ref_date = 2026-02-10（火）` → `2026-02-09（月） 〜 2026-02-15（日）`

### 5.3 Monthly（月次）

基準日 `ref_date` を含む月の **1 日〜末日** を算出する。

```
period_start = ref_date の月の 1 日
period_end   = 翌月 1 日 - 1 日
```

例: `ref_date = 2026-02-10` → `2026-02-01 〜 2026-02-28`

---

## 6. 集計ロジック

### 6.1 ユーザー別レポート状況（user_report_statuses）

1. `users` テーブルから全ユーザーを取得
2. 期間内の `daily_reports` から `user_id` ごとのレポート数を集計（`Counter`）
3. `report_date == today` のレポートがあるか判定
4. 全ユーザー分のリストを返却（レポート数 0 のユーザーも含む）
5. `category_breakdown`: 各ユーザーの分類別レポート数・作業時間（**全カテゴリ分、0 件含む**）

### 6.2 日別レポート推移（report_trends）

1. 期間内の `daily_reports` を `report_date` ごとにカウント
2. 日付昇順でソート
3. レポートが存在する日付のみリストに含まれる（0 件の日は省略）
4. `category_breakdown`: 各日付の分類別レポート数・作業時間（**0 件のカテゴリは除外**）

### 6.3 分類別傾向（category_trends）

1. `task_categories` テーブルから全分類名を取得
2. 期間内の `daily_reports` を `category_id` ごとに集計:
   - `report_count`: 当該分類のレポート件数
   - `total_minutes`: 当該分類の `time_minutes` 合計（NULL は 0 として扱う）
3. `total_minutes` **降順** でソート（作業時間が多い分類が上位）
4. `category_id` に対応する分類名がない場合は `"Unknown"` を表示

### 6.4 最近の日報（recent_reports）

1. 期間内の `daily_reports` を `report_date` 降順で取得
2. 先頭 **10 件** を抽出
3. `work_content` の先頭 100 文字を `work_content_preview` として返却

### 6.5 課題一覧（issues）

1. 期間内の全 `daily_reports` を走査
2. `issues` フィールドが空でないレポートを抽出
3. フォーマット: `"[{report_date}] {display_name}: {issues}"`

---

## 7. フロントエンド

### 7.1 画面構成（`/summary`）

- テンプレート: `templates/summary.html`
- JavaScript: `static/js/summary.js?v=5`
- ナビバー: `bi-graph-up` アイコンで表示

```
Business Summary ページ
├── 期間切替: [Daily | Weekly | Monthly]  ◀ 期間ラベル ▶  [Today]
├── 上段 (row)
│   ├── 左 (col-lg-6): User Report Status カード
│   └── 右 (col-lg-6): Report Trends カード
├── 中段 (row)
│   ├── 左 (col-lg-6): Category Breakdown カード
│   └── 右 (col-lg-6): Issues カード
└── 下段 (row)
    └── 左 (col-lg-6): Recent Reports カード
```

### 7.2 User Report Status

4 列テーブル:

| 列 | 幅 | 内容 |
|----|-----|------|
| User | 120px 固定 | ユーザー表示名 |
| Category Distribution | 残り全幅 | インライン積み上げバー（Bootstrap `.progress`） |
| Total | 60px 固定 | レポート件数（`badge bg-primary`） |
| Today | 60px 固定 | 今日のレポート有無（`bi-check-circle` / `bi-x-circle`） |

**積み上げバー**:
- 各セグメントの幅 = `total_minutes / ユーザー合計 minutes * 100%`（**作業時間ベース**）
- `total_minutes` が全て 0 の場合は `count`（件数）ベースにフォールバック
- 各セグメントに `title` ツールチップ: `カテゴリ名: Xh Ym`
- 非ゼロカテゴリのみセグメント表示（0 件は省略）

**展開行**:
- 行クリック（`.cursor-pointer`）で Bootstrap `collapse` 展開行をトグル
- 展開行: カテゴリ色バッジ一覧（`カテゴリ名: X件 (Xh Ym)` 形式）
- `d-flex flex-wrap gap-1` でバッジをラップ表示
- レポート 0 件のユーザーはバー・展開行なし

### 7.3 Report Trends

- スタック型プログレスバーによる日別・分類別レポート数の横棒グラフ
- 各バーの最大幅 = `count / maxCount * 100%`（最大件数を 100% とする）
- **凡例**: `report_trends` の `category_breakdown` から使用カテゴリ ID を収集し、**データが存在するカテゴリのみ**表示
- 下部に `Total: {total_reports} reports` を表示

### 7.4 Category Breakdown

| 列 | 内容 |
|------|------|
| Category | カテゴリ名 |
| Reports | レポート件数（`badge bg-primary`） |
| Time | 合計作業時間（`Xh Ym` 形式） |

### 7.5 Issues

- リストグループ形式。各課題を 1 行で表示
- フォーマット: `[{report_date}] {display_name}: {issues}`

### 7.6 Recent Reports

- リストグループ形式。日報詳細ページ（`/reports/{id}`）へのリンク付き
- 各エントリ: `report_date` + `display_name` + `work_content_preview`

### 7.7 ナビゲーション動作

| 操作 | Daily モード | Weekly モード | Monthly モード |
|------|------------|-------------|--------------|
| ◀ | ref_date - 1 日 | ref_date - 7 日 | ref_date の前月 |
| ▶ | ref_date + 1 日 | ref_date + 7 日 | ref_date の翌月 |
| Today | ref_date = 今日 | ref_date = 今日 | ref_date = 今日 |
| 切替 | period 変更後に再取得 | period 変更後に再取得 | period 変更後に再取得 |

### 7.8 時間表示フォーマット

`total_minutes` を `Xh Ym` 形式で表示:
- 60 分以上: `2h 30m`
- 60 分未満: `45m`
- 0 分: `0m`

### 7.9 カラーパレット

カテゴリの色分けに 16 色パレットを使用:

```
#0d6efd, #198754, #ffc107, #dc3545, #6f42c1, #fd7e14, #20c997, #e83e8c,
#6610f2, #0dcaf0, #84b6eb, #a3cfbb, #d4a017, #8b4513, #9b59b6, #795548
```

- カテゴリ ID の昇順にパレットインデックスを割り当て（`categories[i] → CATEGORY_COLORS[i]`）
- `buildColorMap(categories)` で `{category_id: color}` マップを生成
- User Report Status のバー、Report Trends のバー、展開行バッジの全てで共有

### 7.10 空データ時の表示

| コンポーネント | 空データ表示 |
|--------------|-----------|
| User Report Status | `"No users"` (colspan=4) |
| Report Trends | `"No data"` (中央揃え) |
| Category Breakdown | `"No data"` (colspan=3) |
| Issues | `"No issues reported"` |
| Recent Reports | `"No reports"` |

---

## 8. ビジネスルール

### 8.1 認可

| 操作 | admin | user |
|------|-------|------|
| GET /api/summary/ | OK | OK |

全認証ユーザーが閲覧可能。データの作成・更新・削除は行わない読み取り専用機能。

### 8.2 集計ルール

| ルール | 説明 |
|--------|------|
| 期間フィルタ | `report_date` が `period_start` 〜 `period_end` の範囲内のレポートのみ集計 |
| 全ユーザー含む | レポート 0 件のユーザーも `user_report_statuses` に含まれる |
| 0 件日は省略 | `report_trends` にはレポートが存在する日付のみ含まれる |
| category_breakdown の差異 | UserReportStatus は全カテゴリ（0 件含む）、ReportTrend は 0 件除外 |
| ソート順 | category_trends は `total_minutes` 降順、report_trends は日付昇順 |
| Unknown カテゴリ | `category_id` に対応するカテゴリが存在しない場合は `"Unknown"` |

---

## 9. ファイル構成

### 9.1 新規作成（5 ファイル）

| ファイル | 内容 |
|---------|------|
| `app/schemas/summary.py` | レスポンススキーマ定義（7 クラス） |
| `app/services/summary_service.py` | 集計ビジネスロジック |
| `app/routers/api_summary.py` | API ルーター（GET /api/summary/） |
| `templates/summary.html` | 画面テンプレート |
| `static/js/summary.js` | クライアント側ロジック |

### 9.2 変更

| ファイル | 変更内容 |
|---------|---------|
| `app/crud/daily_report.py` | `get_reports_by_date_range()` 追加（期間内日報取得） |
| `main.py` | router 登録追加 |
| `app/routers/pages.py` | `/summary` ページルート追加 |
| `templates/base.html` | Summary ナビリンク追加（`bi-graph-up` アイコン） |

---

## 10. テスト

`tests/test_summary.py` に 12 テストケース（`TestSummaryAPI` クラス）。

### 基本集計テスト（3 件）
- レポート 0 件で正常レスポンス（全フィールドの型確認）
- weekly 集計で `total_reports >= 1` の確認
- monthly 集計で `total_reports >= 1` の確認

### Daily テスト（2 件）
- daily 集計で `period_start == period_end == ref_date` の確認
- daily 集計で隣接日のデータが含まれないことの確認

### ユーザー別テスト（2 件）
- `user_report_statuses` にユーザー情報（`report_count`, `display_name`）が含まれることの確認
- ユーザーごとの `category_breakdown`（分類別レポート数・`total_minutes`）の正確性確認

### 分類別テスト（2 件）
- `category_trends` の集計（件数・時間・`total_minutes` 降順ソート）の確認
- レスポンスに `categories` リストが含まれることの確認

### 日別トレンドテスト（1 件）
- `report_trends` の `category_breakdown`（日別・分類別レポート数）の正確性確認

### 課題テスト（1 件）
- `issues` フィールドのテキスト抽出確認

### バリデーションテスト（1 件）
- 不正な `period`（`"yearly"`）で `422` エラーの確認

---

## 11. マイグレーション

Business Summary は専用テーブルを持たない。`daily_reports` テーブル（`c3790ffa7e38`）および `task_categories` テーブル（`709a8464bb48`）に依存する。

---

## 12. グループフィルタ機能（追加仕様）

### 12.1 概要

`groups` テーブル（SPEC_GROUP.md 参照）を利用し、Business Summary をグループ単位でフィルタリングして表示する機能を追加する。

### 12.2 要件

| 項目 | 仕様 |
|------|------|
| フィルタ対象 | `user_report_statuses`, `report_trends`, `category_trends`, `recent_reports`, `issues` の全集計 |
| フィルタ方法 | API パラメータ `group_id` でグループ指定 |
| 未指定時 | 従来通り全ユーザーを集計（後方互換） |
| UI | ナビゲーション横にグループセレクトボックスを配置 |

### 12.3 API 変更

**GET /api/summary/**

クエリパラメータ追加:

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|----------|------|
| `group_id` | int (optional) | None | グループ ID。指定時はそのグループに所属するユーザーの日報のみ集計 |

### 12.4 バックエンド変更

**`app/routers/api_summary.py`**

- `group_id: Optional[int] = Query(None)` パラメータ追加
- `svc_summary.get_summary(db, period, ref_date, group_id)` に引数追加

**`app/services/summary_service.py`**

`get_summary()` に `group_id` 引数追加:

1. `group_id` が指定された場合、`users` を `group_id` でフィルタ
2. フィルタされたユーザー ID セットで `reports` を絞り込み
3. 以降の集計は従来ロジックと同一（ユーザーリスト・レポートが絞り込み済み）

```python
def get_summary(db, period, ref_date, group_id=None):
    ...
    users = crud_user.get_users(db)
    if group_id is not None:
        users = [u for u in users if u.group_id == group_id]

    target_user_ids = {u.id for u in users}
    reports = [r for r in all_reports if r.user_id in target_user_ids]
    ...
```

**影響範囲**:
- `user_report_statuses`: フィルタ後のユーザーのみ表示
- `report_trends`: フィルタ後のレポートのみ集計
- `category_trends`: フィルタ後のレポートのみ集計
- `recent_reports`: フィルタ後のレポートのみ表示
- `issues`: フィルタ後のレポートのみ表示
- `total_reports`: フィルタ後のレポート数
- `categories`: 変更なし（全カテゴリを返す）

### 12.5 フロントエンド変更

**`templates/summary.html`**

ナビゲーション行にグループセレクトボックスを追加:

```html
<select class="form-select form-select-sm" id="group-filter" style="width:180px" onchange="loadSummary()">
    <option value="">All Groups</option>
    <!-- JS で動的生成 -->
</select>
```

**`static/js/summary.js`**

- `init()` で `/api/groups/` を取得し、セレクトボックスに選択肢を追加
- `loadSummary()` で `group_id` パラメータを追加:
  ```js
  let url = `/api/summary/?period=${currentPeriod}&ref_date=${currentRefDate}`;
  const groupId = document.getElementById('group-filter').value;
  if (groupId) url += `&group_id=${groupId}`;
  ```
- キャッシュバスト: `summary.js?v=5` → `v=6`

### 12.6 テスト追加

`tests/test_summary.py` に追加:

| テスト | 説明 |
|--------|------|
| `test_summary_group_filter` | `group_id` 指定で対象グループのユーザーのみ集計されることを確認 |
| `test_summary_group_filter_empty` | 所属ユーザーがいないグループで `total_reports=0` を確認 |
| `test_summary_no_group_filter` | `group_id` 未指定で全ユーザー集計（後方互換）を確認 |

### 12.7 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `app/routers/api_summary.py` | `group_id` パラメータ追加 |
| `app/services/summary_service.py` | `group_id` によるユーザー・レポートフィルタ |
| `templates/summary.html` | グループセレクトボックス追加 |
| `static/js/summary.js` | グループ選択 + API パラメータ連携 |
| `tests/test_summary.py` | グループフィルタテスト ~3件追加 |
