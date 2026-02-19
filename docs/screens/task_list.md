# Task List画面 (`/task-list`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 表示機能

- タブ切替構成:「My Items」（自分の担当、デフォルト）/「All Items」（全体）
- アイテムをテーブル形式で表示
- テーブルカラム: ステータス、タイトル、分類、予定日、作業時間、Backlog、担当者（全体タブのみ）、操作
- ステータスバッジ: open=グレー、in_progress=青、done=緑
- フィルタバー（タブとテーブルの間に配置）:
  - ステータスフィルタ（ボタングループ: All / Open / In Progress / Done）
  - カテゴリフィルタ（ドロップダウン）
  - キーワード検索（タイトル・チケット番号の部分一致、300msデバウンス）
  - Show Done チェックボックス（デフォルトOFF: doneをサーバーサイドで除外）

## 操作機能

- **新規作成**: モーダルダイアログで入力（タイトル、説明、予定日、カテゴリ、Backlogチケット）
- **編集**: モーダルダイアログで既存データを修正
- **削除**: 確認ダイアログ後に削除
- **Assign**: 未割当アイテムを自分に割り当て（All Itemsタブで操作）
- **Unassign**: 割り当て解除（自分の担当のみ操作可能）
- **Start**: アイテムをTasksページにコピー（新しいTaskを作成）、アイテムのステータスをin_progressに変更
- **Done**: アイテムのステータスをdoneに変更

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/task_list.html` |
| JavaScript | `static/js/task_list.js` |
| ルーター | `app/routers/pages.py` (`GET /task-list`) |
| API | `app/routers/api_task_list.py` |
