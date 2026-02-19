# ログイン画面 (`/login`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

`base.html` を継承しない独立ページ。

- 中央配置のカード型ログインフォーム
- 入力フィールド: Email、Password
- ログインボタン押下で `POST /api/auth/login` を呼び出し
- 成功時: `/` にリダイレクト
- 失敗時: フォーム上部にエラーアラート表示

| 項目 | ファイル |
|------|---------|
| テンプレート | `templates/login.html` |
| ルーター | `app/routers/pages.py` (`GET /login`) |
| API | `app/routers/api_auth.py` |
