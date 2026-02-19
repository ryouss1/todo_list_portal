# Tasks画面 (`/tasks`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 表示機能

- タスクをカード形式でグリッド表示（MD: 2列、LG: 3列）
- 各タスクカードに以下を表示:
  - タイトルとステータスバッジ（pending=グレー、in_progress=青）
  - 説明文
  - タイマー表示（HH:MM:SS形式、等幅フォント）
  - Start/Stopボタン
  - Edit/Deleteボタン

## 操作機能

- **新規作成**: モーダルダイアログで入力（タイトル、説明、タスク分類、Backlogチケット番号）
- **編集**: モーダルダイアログで修正（タイトル、説明、ステータス、タスク分類、Backlogチケット番号）。ステータス選択は編集時のみ表示。
- **削除**: 確認ダイアログ後に削除
- **タイマー開始**: Startボタンでタイマー開始。タイマー中はリアルタイムでカウントアップ表示。
- **タイマー停止**: Stopボタンでタイマー停止。経過時間が累計に加算される。
- **Done**: タスクを完了（report=true時は日報自動作成）。
- **Batch-Done**: Overdueタスクの一括完了モーダル。
- アクティブなタイマーがある場合、ページロード時に自動検出してカウントアップを再開する。

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/tasks.html` |
| JavaScript | `static/js/tasks.js` |
| ルーター | `app/routers/pages.py` (`GET /tasks`) |
| API | `app/routers/api_tasks.py` |
