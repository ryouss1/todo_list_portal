# Presence画面 (`/presence`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 表示機能

- 全ユーザーの在籍状態をカード形式で一覧表示
- 各ユーザーの表示名、ステータスバッジ、ステータスメッセージを表示
- 作業中タスクのBacklogチケットをリンク付きで表示

## 操作機能

- **ステータス変更**: ドロップダウンで自分のステータスを変更
- **メッセージ入力**: ステータスメッセージの設定
- WebSocket経由で他ユーザーの状態変更をリアルタイム反映

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/presence.html` |
| JavaScript | `static/js/presence.js` |
| ルーター | `app/routers/pages.py` (`GET /presence`) |
| API | `app/routers/api_presence.py` |
| WebSocket | `main.py` (`WS /ws/presence`) |
