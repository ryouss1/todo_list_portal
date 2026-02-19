# Summary画面 (`/summary`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

- 期間（日次/週次/月次）の切り替え
- 日報件数、ユーザー別提出状況、カテゴリ別集計を表示
- 課題・問題の集約表示

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/summary.html` |
| JavaScript | `static/js/summary.js` |
| ルーター | `app/routers/pages.py` (`GET /summary`) |
| API | `app/routers/api_summary.py` |
