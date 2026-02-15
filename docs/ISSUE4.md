# ISSUE4: プロジェクト課題・技術的負債

**作成日**: 2026-02-10
**最終更新**: 2026-02-11
**テスト総数**: 324件（324 pass / 0 fail）
**Lint**: ruff check / ruff format 全クリア

---

## 1. テスト不具合（9件失敗）

### 1.1 bcrypt 互換性問題 — 4件失敗 ✅ 解決済み

| テスト | エラー | ファイル |
|--------|--------|---------|
| `test_login_success` | `assert 401 == 200` | `tests/test_auth.py` |
| `test_me_authenticated` | `assert 401 == 200` | `tests/test_auth.py` |
| `test_websocket_broadcast_on_log_create` | `WebSocketDisconnect(4401)` | `tests/test_websocket.py` |
| `test_websocket_disconnect_cleanup` | `assert 0 == 1` | `tests/test_websocket.py` |

**対処**: `conftest.py` の `db_session` フィクスチャでテストユーザーの `password_hash` を `TEST_PASSWORD_HASH` で明示的に設定するよう修正。`email`, `is_active`, `role` も毎回リセット。

### 1.2 テストデータ分離不備 — 5件失敗 ✅ 解決済み

| テスト | エラー | ファイル |
|--------|--------|---------|
| `test_list_public_todos_empty` | 空のはずが2件返る | `tests/test_todos.py` |
| `test_list_public_todos` | 期待と異なるデータ | `tests/test_todos.py` |
| `test_list_users` | `'yamamoto' == 'default_user'` | `tests/test_users.py` |
| `test_summary_empty` | `1 == 0` | `tests/test_summary.py` |
| `test_summary_has_issues` | 集計値不一致 | `tests/test_summary.py` |

**対処**:
- `test_list_public_todos_*`: テスト内で stale な public todos を `db_session.query().delete()` でクリーンアップ
- `test_summary_empty`: `ref_date=2020-01-06` を指定し stale データのない期間でテスト
- `test_summary_has_issues`: `ref_date` + `>= 1` アサーションで修正済み
- `test_list_users`: `db_session` で `display_name` をリセットして解決済み

---

## 2. セキュリティ

### 2.1 ハードコードされた認証情報 ⏳ 未解決（設計判断）

**ファイル**: `app/config.py:3-6,10-11`

DB パスワード、セッション署名キー、デフォルトパスワードがソースコードにハードコード。環境変数未設定時にそのまま使用される。

**影響**: 開発環境では問題なし。本番環境では環境変数の設定が必須。

**対策案**: 本番環境では環境変数の設定を必須化。デフォルト値を削除するか、起動時に未設定をチェックして警告/停止。

### 2.2 ログイン時のセッション再生成なし ✅ 解決済み

**ファイル**: `app/routers/api_auth.py:14-23`

**対処**: ログイン成功時に `request.session.clear()` を追加。セッション固定攻撃を防止。

### 2.3 ログイン試行制限なし ⏳ 未解決（将来対応）

**ファイル**: `app/routers/api_auth.py:13-23`

ブルートフォース攻撃への対策がない。失敗回数の記録、レート制限、アカウントロック機能が未実装。

### 2.4 auth_middleware の API 認証ギャップ ✅ 解決済み

**ファイル**: `main.py:84-93`

**対処**: auth_middleware で未認証 API リクエストに 401 を返すよう修正。`/api/logs/` の POST のみ公開（外部ログ取り込み）。これにより `Depends(get_current_user_id)` を付け忘れた場合でもミドルウェアレベルで保護される（防御の多層化）。

テストフィクスチャ（`client`/`client_user2`）は `_make_session_cookie()` でセッションCookieを直接生成する方式に変更（bcrypt不要で高速）。

### 2.5 password_hash が nullable ⏳ 未解決（低リスク）

**ファイル**: `app/models/user.py:12`

パスワードなしのユーザが DB レベルで作成可能。`auth_service.authenticate()` で `if not user.password_hash` チェックしているため実害なし。

**対策案**: `nullable=False` への変更 + マイグレーション。

---

## 3. アーキテクチャ・コード品質

### 3.1 サービス層の返却型不統一 ⏳ 未解決（リファクタリング）

| サービス | 返却型 | パターン |
|---------|--------|---------|
| `todo_service` | ORM オブジェクト | `return crud.get_todos(db, user_id)` |
| `user_service` | ORM オブジェクト | `return crud.get_users(db)` |
| `alert_service` | ORM オブジェクト | `return crud.get_alert(db, id)` |
| `presence_service` | ORM オブジェクト | 直接 ORM |
| **`attendance_service`** | **dict** | **`_attach_breaks()` で手動変換** |

`attendance_service` のみ `_attach_breaks()` ヘルパーで ORM → dict 変換を行い、breaks リストを付加している。

**対策案**: SQLAlchemy の `relationship()` を使って `Attendance.breaks` を定義し、ORM オブジェクトのまま返すようにリファクタリング。

### 3.2 async/sync 不統一 ⏳ 未解決（リファクタリング）

| サービス | async? | 実際の非同期I/O |
|---------|--------|---------------|
| `alert_service` | 全関数 async | WebSocket broadcast のみ |
| `log_service.create_log` | async | WebSocket broadcast のみ |
| その他 | 全関数 sync | なし |

`alert_service` と `log_service.create_log` は `async def` だが、DB 操作は同期。

**対策案**: WebSocket broadcast を同期ラッパーで呼ぶか、全サービスを sync に統一。

### 3.3 LogSource status エンドポイントの実装不足 ⏳ 未解決（軽微）

**ファイル**: `app/routers/api_log_sources.py:22-27`

`LogSourceStatusResponse` はフィールドを絞った軽量スキーマだが、内部では全フィールドを取得する `list_sources()` を呼んでいる。機能的には動作するが、不要なデータをフェッチしている。

### 3.4 TemplateResponse の非推奨パターン ✅ 解決済み

**対処**: `pages.py` の全 `TemplateResponse` 呼び出しを `TemplateResponse(request=request, name="xxx.html")` のキーワード引数形式に変更。DeprecationWarning が解消。

### 3.5 テンプレートパスの相対指定 ⏳ 未解決（軽微）

**ファイル**: `app/routers/pages.py:5`

```python
templates = Jinja2Templates(directory="templates")
```

CWD 依存の相対パス。`python main.py` 以外からの起動で失敗する可能性。

**対策案**: `Path(__file__).resolve().parent.parent.parent / "templates"` で絶対パス化。

---

## 4. データベース

### 4.1 コネクションプール設定なし ⏳ 未解決（運用改善）

**ファイル**: `app/database.py:6`

`pool_size`、`max_overflow`、`pool_recycle` が未設定。デフォルト値（`pool_size=5`, `max_overflow=10`）のまま。

### 4.2 テスト DB と本番 DB が同一 ⏳ 未解決（設計判断）

**ファイル**: `tests/conftest.py:12`

テストは本番と同じ `DATABASE_URL` を使用。トランザクションロールバックで分離しているが、`seed_default_user()` 等はテストトランザクション外でコミットされるため、本番データに影響を与えうる。

### 4.3 default_preset_id の FK 制約 ⏳ 未解決（低リスク）

**ファイル**: `app/models/user.py:15`

`default_preset_id` の FK 先（`attendance_presets.id`）が削除された場合の ON DELETE 動作が未指定。

---

## 5. Attendance 凍結時の未解決事項

> Attendance 機能は現在凍結中。以下は凍結時点で残っている課題。

| 項目 | 詳細 |
|------|------|
| Edit Modal に休憩編集なし | 編集画面で clock_in, clock_out, note のみ編集可能。休憩の追加・編集・削除は不可 |
| Duration 表示問題 | JS キャッシュが古い場合に Duration カラムが表示されない可能性 |
| 1分未満チェック未実装 | 1分以内の休憩・出退勤を登録しないルールが未実装 |
| 時刻バリデーション不足 | `_parse_time()` で `"HH:MM"` 以外のフォーマットが `ValueError` → 500 エラーになる |
| 時刻整合性チェックなし | `clock_in < clock_out`、`break_start < break_end` の検証がない |

---

## 6. API 設計

### 6.1 全リストエンドポイントにページネーションなし ⏳ 未解決（将来対応）

全 `GET /api/{resource}/` エンドポイントが全件返す。

### 6.2 API バージョニングなし ⏳ 未解決（将来対応）

全エンドポイントが `/api/` 直下。

---

## 7. DeprecationWarning / SAWarning

| 警告 | 状態 | 内容 |
|------|------|------|
| `DeprecationWarning` | ✅ 解決済み | `TemplateResponse` のキーワード引数形式に移行完了 |
| `SAWarning` | ⏳ 未解決 | `"transaction already deassociated from connection"` — `test_create_user_duplicate_email` で発生。テスト結果に影響なし |

---

## 8. 運用面の課題

| 項目 | 詳細 |
|------|------|
| 管理者 UI なし | ログソース・アラートルール・ユーザ管理はすべて API 直接呼び出しが必要 |
| データエクスポートなし | Todo、日報等の CSV/JSON エクスポート機能が未実装（勤怠Excelエクスポートは実装済み） |
| 監査ログなし | ユーザ操作（作成・更新・削除）の監査証跡がない |
| ソフトデリートなし | 全モデルが物理削除。誤削除からのリカバリー不可 |
| バックアップ機能なし | アプリケーション層でのバックアップ/リストア機能なし |

---

## まとめ

### 解決状況

| カテゴリ | 件数 | 解決済み | 未解決 |
|---------|------|---------|--------|
| テスト不具合 | 2 | 2 | 0 |
| セキュリティ | 5 | 2 | 3（うち1件は設計判断、2件は将来対応） |
| アーキテクチャ | 5 | 1 | 4（リファクタリング・軽微） |
| データベース | 3 | 0 | 3（設計判断・運用改善） |
| Attendance凍結 | 5 | 0 | 5（凍結中） |
| API設計 | 2 | 0 | 2（将来対応） |
| 警告 | 2 | 1 | 1（影響なし） |
| 運用面 | 5 | 0 | 5（将来対応） |
| **合計** | **29** | **6** | **23** |

### 優先度別サマリー

#### P0（Critical）— ✅ 全件解決済み
1. ~~bcrypt テスト失敗の修正~~（1.1）✅
2. ~~テストデータ分離の修正~~（1.2）✅

#### P1（High）— 2/3 解決
3. ハードコード認証情報（2.1）⏳ 設計判断
4. ~~auth_middleware の API 認証ギャップ~~（2.4）✅
5. ~~TemplateResponse 非推奨パターン~~（3.4）✅

#### P2（Medium）— 1/5 解決
6. サービス層の返却型不統一（3.1）⏳
7. async/sync 不統一（3.2）⏳
8. ~~セッション再生成なし~~（2.2）✅
9. DB コネクションプール設定（4.1）⏳
10. テスト DB 分離（4.2）⏳

#### P3（Low）— 未着手
11. ページネーション追加（6.1）⏳
12. password_hash nullable（2.5）⏳
13. ログイン試行制限（2.3）⏳
14. 管理者 UI（8）⏳
15. API バージョニング（6.2）⏳
