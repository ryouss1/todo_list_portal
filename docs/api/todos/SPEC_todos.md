# Todo API 仕様 (`/api/todos`)

> 本ドキュメントは [SPEC_API.md](./SPEC_API.md) から分割された Todo API の仕様です。
> 全体仕様は [SPEC.md](./SPEC.md) を参照してください。

---

## 概要

Todo API はログインユーザーの Todo アイテムの CRUD と、公開 Todo 一覧の取得を提供する。
全エンドポイントに認証が必要。操作は自分の Todo のみ（公開一覧は全員分閲覧可）。

| メソッド | パス | 説明 | ステータスコード |
|---------|------|------|----------------|
| GET | `/api/todos/` | 自分の Todo 一覧取得 | 200 |
| POST | `/api/todos/` | Todo 作成 | 201 |
| GET | `/api/todos/public` | 公開 Todo 一覧取得 | 200 |
| GET | `/api/todos/{todo_id}` | Todo 詳細取得 | 200 / 404 |
| PUT | `/api/todos/{todo_id}` | Todo 更新 | 200 / 404 |
| DELETE | `/api/todos/{todo_id}` | Todo 削除 | 204 / 404 |
| PATCH | `/api/todos/{todo_id}/toggle` | Todo 完了トグル | 200 / 404 |

---

## GET /api/todos/

ログインユーザーの Todo 一覧を取得する。優先度降順・作成日時降順でソートされる。

### レスポンス

- **成功**: `200 OK` - `TodoResponse[]`

### 処理フロー

1. セッションから `user_id` を取得
2. `user_id` に紐づく Todo を `priority DESC`, `created_at DESC` で取得
3. `TodoResponse[]` を返却

---

## POST /api/todos/

新しい Todo を作成する。

### リクエストボディ: `TodoCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | タイトル |
| description | string | No | null | 説明 |
| priority | integer | No | 0 | 優先度 (0=Normal / 1=High / 2=Urgent) |
| due_date | date (YYYY-MM-DD) | No | null | 期日 |
| visibility | string | No | "private" | 公開範囲 ("private" / "public") |

### レスポンス

- **成功**: `201 Created` - `TodoResponse`
- **エラー**: `422 Unprocessable Entity` - バリデーションエラー（title 未指定、不正な visibility 等）

### 処理フロー

1. リクエストボディをバリデーション
2. `user_id` を紐づけて Todo を DB に作成
3. `TodoResponse` を返却

---

## GET /api/todos/public

全ユーザーの公開 Todo 一覧を取得する（`visibility="public"` の Todo のみ）。

### レスポンス

- **成功**: `200 OK` - `TodoResponse[]`

### 処理フロー

1. `visibility="public"` の Todo を全件取得
2. `TodoResponse[]` を返却

### 注意

- 公開 Todo は閲覧のみ可能。他ユーザーの公開 Todo を編集・削除することはできない（`404` が返る）。

---

## GET /api/todos/{todo_id}

指定 ID の Todo を取得する。自分の Todo のみ取得可能。

### レスポンス

- **成功**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found` - Todo 不存在、または他ユーザーの Todo

---

## PUT /api/todos/{todo_id}

指定 ID の Todo を更新する。指定されたフィールドのみ更新（部分更新対応）。

### リクエストボディ: `TodoUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | No | タイトル |
| description | string | No | 説明 |
| priority | integer | No | 優先度 |
| due_date | date | No | 期日 |
| is_completed | boolean | No | 完了フラグ |
| visibility | string | No | 公開範囲 ("private" / "public") |

### レスポンス

- **成功**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found` - Todo 不存在、または他ユーザーの Todo

---

## DELETE /api/todos/{todo_id}

指定 ID の Todo を削除する。自分の Todo のみ削除可能。

### レスポンス

- **成功**: `204 No Content`
- **エラー**: `404 Not Found` - Todo 不存在、または他ユーザーの Todo

---

## PATCH /api/todos/{todo_id}/toggle

指定 ID の Todo の完了状態をトグルする（`true ↔ false`）。

### レスポンス

- **成功**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found` - Todo 不存在、または他ユーザーの Todo

---

## スキーマ

### TodoCreate

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | タイトル |
| description | string | No | null | 説明 |
| priority | integer | No | 0 | 優先度 (0=Normal / 1=High / 2=Urgent) |
| due_date | date | No | null | 期日 |
| visibility | string | No | "private" | 公開範囲 ("private" / "public") |

### TodoUpdate

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | No | タイトル |
| description | string | No | 説明 |
| priority | integer | No | 優先度 |
| due_date | date | No | 期日 |
| is_completed | boolean | No | 完了フラグ |
| visibility | string | No | 公開範囲 ("private" / "public") |

### TodoResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | Todo ID |
| user_id | integer | ユーザーID |
| title | string | タイトル |
| description | string \| null | 説明 |
| is_completed | boolean | 完了フラグ |
| priority | integer | 優先度 |
| due_date | date \| null | 期日 |
| visibility | string | 公開範囲 ("private" / "public") |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---

## データモデル

### todos テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | Todo ID |
| user_id | Integer | FK(users.id), NOT NULL | 所有ユーザーID |
| title | String(500) | NOT NULL | タイトル |
| description | Text | NULL許可 | 説明 |
| is_completed | Boolean | DEFAULT false | 完了フラグ |
| priority | Integer | DEFAULT 0 | 優先度 |
| due_date | Date | NULL許可 | 期日 |
| visibility | String(20) | NOT NULL, server_default 'private' | 公開範囲 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

### priority 値

| 値 | 説明 |
|----|------|
| 0 | Normal（通常） |
| 1 | High（高） |
| 2 | Urgent（緊急） |

### visibility 値

| 値 | 説明 |
|----|------|
| `private` | プライベート（本人のみ閲覧・操作可能） |
| `public` | 公開（全認証ユーザーが閲覧可能、操作は本人のみ） |

---

## 認可ルール

| 操作 | 権限 |
|------|------|
| 自分の Todo 一覧 (GET /) | 認証ユーザー（自分の Todo のみ） |
| 公開 Todo 一覧 (GET /public) | 認証ユーザー（全ユーザーの public Todo） |
| Todo 作成 (POST) | 認証ユーザー |
| Todo 取得 (GET /{id}) | 認証ユーザー（自分の Todo のみ） |
| Todo 更新 (PUT /{id}) | 認証ユーザー（自分の Todo のみ） |
| Todo 削除 (DELETE /{id}) | 認証ユーザー（自分の Todo のみ） |
| Todo トグル (PATCH /{id}/toggle) | 認証ユーザー（自分の Todo のみ） |

- 他ユーザーの Todo にアクセスした場合は `404 Not Found` を返す（ID の存在を漏洩しない）。
- 公開 Todo であっても、他ユーザーによる編集・削除・トグルは不可（`404`）。

---

## 実装ファイル

| ファイル | 役割 |
|---------|------|
| `app/models/todo.py` | `Todo` モデル定義 |
| `app/schemas/todo.py` | `TodoCreate`, `TodoUpdate`, `TodoResponse` スキーマ |
| `app/crud/todo.py` | Todo CRUD 操作 |
| `app/services/todo_service.py` | Todo ビジネスロジック + 公開 Todo 一覧 |
| `app/routers/api_todos.py` | Todo REST API（7 エンドポイント） |
| `templates/todos.html` | Todo 画面テンプレート |
| `templates/todos_public.html` | 公開 Todo 一覧画面テンプレート |
| `static/js/todos.js` | Todo 画面 JS |
| `static/js/todos_public.js` | 公開 Todo 一覧 JS |

---

## テスト

`tests/test_todos.py` に 17 テストケース。

| テストケース | 検証内容 |
|-------------|---------|
| test_list_todos_empty | 空の一覧取得で200が返る |
| test_create_todo | 全フィールド指定でTodo作成 |
| test_create_todo_minimal | タイトルのみでTodo作成 |
| test_get_todo | ID指定でTodo取得 |
| test_get_todo_not_found | 存在しないIDで404 |
| test_update_todo | タイトル更新 |
| test_delete_todo | 削除後に取得で404 |
| test_toggle_todo | 完了トグルの往復 |
| test_create_todo_with_due_date | 期日付きTodo作成 |
| test_create_todo_missing_title | タイトル未指定で422 |
| test_create_todo_default_visibility | デフォルトvisibilityがprivate |
| test_create_todo_public | visibility=publicでTodo作成 |
| test_create_todo_invalid_visibility | 不正なvisibilityで422 |
| test_update_visibility | private→public変更 |
| test_list_public_todos_empty | 公開Todo一覧が空 |
| test_list_public_todos | 公開Todoのみ一覧に表示 |
| test_own_list_includes_all_visibilities | 自分の一覧はprivate/public両方 |

`tests/test_authorization.py` に関連する認可テスト（7 件）:

| テストケース | 検証内容 |
|-------------|---------|
| test_get_other_user_todo | 他ユーザーのTodo取得で404 |
| test_update_other_user_todo | 他ユーザーのTodo更新で404 |
| test_delete_other_user_todo | 他ユーザーのTodo削除で404 |
| test_toggle_other_user_todo | 他ユーザーのTodoトグルで404 |
| test_public_todo_visible_to_other_user | 公開Todoが他ユーザーに表示される |
| test_private_todo_not_in_public_list | privateTodoは公開一覧に非表示 |
| test_cannot_modify_other_user_public_todo | 他ユーザーの公開Todoは編集不可（404） |

---

## マイグレーション

| リビジョン | 説明 |
|-----------|------|
| `53797f9c29e5` | 初期スキーマ（todos テーブル含む） |
| `86da56d0b359` | `todos.visibility` カラム追加 |

---

## 備考

- Todo / Public Todos は Task List（Phase 9）で代替されたため、ナビバーから非表示（`d-none`）。URL による直接アクセスは引き続き可能。
- フロントエンドではフィルターボタン（All / Active / Completed）でクライアント側フィルタリングを実行。
- 優先度バッジ: High=黄色、Urgent=赤色。完了済みは取り消し線スタイルで表示。
