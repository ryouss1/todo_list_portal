# Reports画面 (`/reports`, `/reports/{id}`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 日報一覧画面 (`/reports`)

### 表示機能

- 自分の日報一覧をテーブル形式で表示
- 全ユーザーの日報一覧の切り替え表示

### 操作機能

- **新規作成**: モーダルダイアログで入力（対象日、タスク分類、タスク名、作業時間、業務内容等）
- **詳細表示**: 日報詳細画面への遷移

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/reports.html` |
| JavaScript | `static/js/reports.js` |
| ルーター | `app/routers/pages.py` (`GET /reports`) |
| API | `app/routers/api_reports.py` |

## 日報詳細画面 (`/reports/{id}`)

- 日報の全フィールドを詳細表示
- 所有者のみ編集・削除が可能

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/report_detail.html` |
| JavaScript | `static/js/report_detail.js` |
| ルーター | `app/routers/pages.py` (`GET /reports/{report_id}`) |
