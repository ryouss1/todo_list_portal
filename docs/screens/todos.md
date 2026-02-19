# Todo画面 (`/todos`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 表示機能

- Todo一覧をカード形式で表示
- フィルターボタン: All / Active / Completed
- 各Todoに完了チェックボックス、編集ボタン、削除ボタンを配置
- 優先度バッジ: High（黄色）、Urgent（赤色）
- 期日の表示（カレンダーアイコン付き）
- 完了済みTodoは取り消し線スタイルで表示

## 操作機能

- **新規作成**: モーダルダイアログで入力（タイトル、説明、優先度、期日）
- **編集**: モーダルダイアログで既存データを修正
- **削除**: 確認ダイアログ後に削除
- **完了トグル**: チェックボックスで完了状態を切り替え

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/todos.html` |
| JavaScript | `static/js/todos.js` |
| ルーター | `app/routers/pages.py` (`GET /todos`) |
| API | `app/routers/api_todos.py` |
