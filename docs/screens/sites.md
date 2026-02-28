# Sites画面 (`/sites`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## ファイル構成

| 種別 | ファイル |
|------|---------|
| テンプレート | `templates/sites.html` |
| JavaScript | `static/js/sites.js` |
| CSS | `static/css/sites.css` |
| ルーター | `app/routers/api_sites.py` |
| API | `/api/sites/*`, `/api/site-groups/*` |
| WebSocket | `/ws/sites` |

## 表示機能

- サイトリンクをグループごとにカード表示
- グループ未所属のリンクは「未分類」セクションに表示
- 各リンクにステータスバッジ（up/down/error/unknown）を表示
- レスポンス時間、最終チェック日時を表示
- WebSocket (`/ws/sites`) でヘルスチェック結果をリアルタイム更新

## 操作機能

- **Add Link**（右上ボタン）: グループを後から選択してサイトリンクを新規作成
- **+ 追加**（グループ行ボタン）: そのグループを事前選択した状態でリンク追加モーダルを開く
- **Edit Link**: サイトリンクを編集（作成者のみ）
- **Delete Link**: サイトリンクを削除（作成者のみ、確認ダイアログ）
- **Check now**: 手動ヘルスチェック実行（リンク編集モーダル内）
- **Add Group**: サイトグループを新規作成（admin のみ）
- **Edit Group**: サイトグループを編集（admin のみ。グループ行の鉛筆アイコン）
- **Delete Group**: サイトグループを削除（admin のみ。グループ編集モーダル内の Delete ボタン。グループ内リンクは未分類へ移動）

## 自動更新バッジ

画面右上の「自動更新 ●」バッジをクリックすることで WebSocket 自動更新を ON/OFF 切り替えできる。

| 状態 | 表示 | 色 |
|------|------|----|
| 接続済み | 自動更新 ● | 緑 |
| 再接続待ち | 再接続中... | 黄 |
| 停止中 | 自動更新 OFF | グレー |

## リンクモーダル

| フィールド | 入力種別 | 必須 | 説明 |
|-----------|---------|------|------|
| Name | テキスト | Yes | サイト名 |
| URL | URL | Yes | http:// または https:// |
| Description | テキストエリア | No | 説明 |
| Group | セレクト | No | サイトグループ |
| Sort Order | 数値 | No | 表示順（デフォルト 0） |
| Enabled | チェックボックス | No | 有効/無効 |
| Check Enabled | チェックボックス | No | ヘルスチェック有効/無効 |
| Check Interval | 数値 | No | チェック間隔（秒、60〜3600） |
| Timeout | 数値 | No | タイムアウト（秒、3〜60） |
| SSL Verify | チェックボックス | No | SSL証明書検証 |

## グループモーダル

| フィールド | 入力種別 | 必須 | 説明 |
|-----------|---------|------|------|
| Name | テキスト | Yes | グループ名 |
| Description | テキストエリア | No | 説明 |
| Color | カラーピッカー | No | 表示色（デフォルト #6c757d） |
| Icon | テキスト | No | Bootstrap Iconsクラス名 |
| Sort Order | 数値 | No | 表示順（デフォルト 0） |
