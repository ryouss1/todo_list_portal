# Dashboard画面 (`/`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

各機能のサマリーをカード形式で表示する。

- **Todoカード**: 未完了件数 / 全件数
- **Attendanceカード**: 現在の出勤状態（Clocked In / Not Clocked In）
- **Tasksカード**: 作業中タスク数 / 全タスク数
- **Logsカード**: 直近のログ件数
- **Recent Logs**: 直近5件のログをリスト表示（重要度バッジ付き）
- **Incomplete Todos**: 未完了のTodo上位5件をリスト表示（優先度バッジ付き）

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/index.html` |
| ルーター | `app/routers/pages.py` (`GET /`) |
