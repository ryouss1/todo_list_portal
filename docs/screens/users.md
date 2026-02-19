# Users画面 (`/users`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 表示機能

- ユーザー一覧をテーブル形式で表示（メール、表示名、ロール、有効フラグ）

## 操作機能

- **ユーザー作成**: 管理者のみモーダルダイアログで作成
- **ユーザー編集**: 管理者は全フィールド、一般ユーザーは自分の表示名のみ
- **ユーザー削除**: 管理者のみ（自分自身は削除不可）
- **パスワードリセット**: 管理者が他ユーザーのパスワードを強制リセット

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/users.html` |
| JavaScript | `static/js/users.js` |
| ルーター | `app/routers/pages.py` (`GET /users`) |
| API | `app/routers/api_users.py` |
