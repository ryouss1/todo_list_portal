# 仕様・実装 Issue 一覧

> Phase 1（認証基盤）完了時点での仕様書・実装の問題点を網羅的に整理したもの。
> 重要度: **Critical** > **High** > **Medium** > **Low**

---

## 1. セキュリティ

### ISSUE-001: 認可バイパス — 他ユーザーのデータに無制限アクセス可能 [Critical] [解決済み]

**現象**: 認証済みユーザーであれば、他のユーザーのTodo/Task/Attendanceに対してIDを指定するだけでアクセス・変更・削除ができる。

**該当コード**:
```
app/routers/api_todos.py:24-41       — GET/PUT/DELETE/PATCH に user_id チェックなし
app/routers/api_tasks.py:24-51       — GET/PUT/DELETE/POST(start/stop/entries) に user_id チェックなし
app/routers/api_attendances.py:38-40 — GET /{id} に user_id チェックなし
```

**根本原因**: `list` と `create` はルーターで `Depends(get_current_user_id)` を使い user_id をサービスに渡すが、個別操作（GET/PUT/DELETE）では user_id を取得すらしていない。サービス層にも所有者検証がない。

**影響**: 認証済みの全ユーザーが、IDの推測（連番）により他ユーザーの全データを閲覧・改竄・削除可能。

**対処案**: サービス層に `user_id` を渡し、CRUD取得後に `todo.user_id != user_id` なら `NotFoundError` or 新設の `ForbiddenError(403)` を raise する。

**仕様書との乖離**: SPEC_API.md では全エンドポイントに「認証: 必要」と記載しているが、「認可」（自分のデータのみ操作可能）の仕様が明文化されていない。

---

### ISSUE-002: ユーザー管理API に認可なし [High] [解決済み]

**現象**: `POST /api/users/`（ユーザー作成）に管理者チェックがない。認証済みの全ユーザーが新規ユーザーを作成できる。

**該当コード**: `app/routers/api_users.py:18-20` — `get_current_user_id` すら使用していない。

**仕様書との乖離**: SPEC_ROADMAP.md 2.1 に「ユーザー登録: 管理者のみ」と記載しているが、RBAC（`role` カラム）が未実装のため制御不可能。

**対処案**: 暫定策として `get_current_user_id` を追加し認証必須にする。本格対応は `role` カラム追加 + admin チェック。

---

### ISSUE-003: WebSocket `/ws/logs` が認証不要 [Medium]

**現象**: `/ws/logs` は認証なしで接続可能。ログデータのリアルタイム配信を誰でも傍受できる。

**仕様書上の扱い**: SPEC_ROADMAP.md で「Phase 2以降で対応」と明記されている。ただし `/api/logs/*` も認証不要のため、ログデータ自体は公開扱いであり、整合性はとれている。

**対処案**: Phase 2で WebSocket 接続時に Cookie 認証を実装する。

---

## 2. 仕様書の記述誤り・不整合

### ISSUE-004: SPEC_API.md — 「デフォルトユーザー」の記述が残存 [Medium] [解決済み]

**箇所**: SPEC_API.md セクション 1（Todo API）冒頭

> `Todo一覧を取得する。デフォルトユーザー（user_id=1）のTodoを、優先度降順・作成日時降順で返却する。`

**問題**: Phase 1 で認証を導入済みのため、「デフォルトユーザー（user_id=1）」は不正確。「ログインユーザーのTodo」が正しい。

**影響を受ける箇所**: 同ファイル内の Attendance API、Task API の説明文にも同様の表現がある可能性。

---

### ISSUE-005: SPEC.md — テクノロジースタック表が不完全 [Medium] [解決済み]

**箇所**: SPEC.md セクション 1.1「システム構成」テーブル

**不足項目**:
| 追加すべき項目 | 値 |
|---------------|-----|
| DBマイグレーション | Alembic 1.14.1 |
| パスワードハッシュ | passlib[bcrypt] 1.7.4 |
| セッション署名 | itsdangerous 2.2.0 |
| コード品質 | Ruff |

---

### ISSUE-006: SPEC_NONFUNC.md — テストケース数の不一致 [Low] [解決済み]

**箇所**: SPEC_NONFUNC.md セクション 6.2

| テストファイル | 記載 | セクション6.3の実リスト |
|---------------|------|----------------------|
| test_todos.py | 10件 | 10件（OK） |
| test_attendances.py | 10件 | 10件（OK） |
| test_tasks.py | 13件 | 13件（OK） |

**注**: 現時点では一致している。ただし 6.2 のサマリーテーブルと 6.3 のテストケース一覧は手動同期が必要で、今後のテスト追加時にずれるリスクがある。

---

## 3. テストの考慮不足

### ISSUE-007: データ所有者分離のテストが存在しない [High] [解決済み]

**現象**: テストは全て `user_id=1` の単一ユーザーで実行される。別ユーザーのデータにアクセスできないことを検証するテストがない。

**影響**: ISSUE-001 の認可バイパスがテストで検出されない。

**必要なテスト例**:
- User A が作成した Todo を User B が GET/PUT/DELETE しようとした場合に 403/404 になること
- User A の Attendance を User B が取得できないこと

---

### ISSUE-008: User API のテストが存在しない [High] [解決済み]

**現象**: `tests/test_users.py` が存在しない。`/api/users/` の3エンドポイント（一覧取得・作成・ID取得）がテストされていない。

**不足テスト**:
- `GET /api/users/` — ユーザー一覧取得
- `POST /api/users/` — ユーザー作成（password フィールドのバリデーション含む）
- `GET /api/users/{id}` — ユーザー取得
- `POST /api/users/` — 重複 email で適切なエラーが返ること

---

### ISSUE-009: WebSocket のテストが存在しない [Medium] [解決済み]

**現象**: `/ws/logs` の接続・切断・ブロードキャスト動作がテストされていない。

**不足テスト**:
- WebSocket 接続成功
- ログ作成時にブロードキャストされること
- 切断後のクリーンアップ

---

### ISSUE-010: UserCreate スキーマの password バリデーションが未テスト [Medium] [解決済み]

**現象**: `UserCreate` に `password` フィールドが必須で追加されたが、テストがないため以下が未検証:
- password 未指定で 422 が返ること
- パスワードが DB にハッシュ化されて保存されること（平文保存されていないこと）

---

## 4. アーキテクチャ上の問題

### ISSUE-011: TodoUpdate スキーマが API 仕様と不一致 [Medium] [解決済み]

**SPEC_API.md の仕様**: TodoUpdate の全フィールドは Optional。

**実装** (`app/schemas/todo.py:18-20`):
```python
class TodoUpdate(TodoBase):      # TodoBase から title: str, description, priority, due_date を継承
    title: Optional[str] = None  # 上書きで Optional にしている
    is_completed: Optional[bool] = None
```

**問題**: `TodoBase` の `priority: int = 0` と `description: Optional[str] = None` はデフォルト値があるため表面上動作するが、`TodoUpdate` が `TodoBase` を継承する設計意図が不明瞭。CRUD 側で `exclude_unset=True` により実害はないが、スキーマだけを見たとき「priority を指定しなかったら 0 に上書きされる」と誤解しやすい。

**対処案**: `TodoUpdate` を `TodoBase` から継承せず、全フィールドを明示的に `Optional` で定義する。

---

### ISSUE-012: on_event("startup") が非推奨 [Low] [解決済み]

**箇所**: `main.py:61`

```python
@app.on_event("startup")
def on_startup():
```

**問題**: FastAPI 0.93+ で非推奨（`lifespan` コンテキストマネージャ推奨）。テスト実行時に `DeprecationWarning` が出力される。

**対処案**:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_default_user()
    yield

app = FastAPI(title="Todo List Portal", lifespan=lifespan)
```

---

### ISSUE-013: logout 関数が base.html にインライン定義 [Low] [解決済み]

**箇所**: `templates/base.html` 内の `<script>` ブロック

```javascript
async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
}
```

**問題**: JS の共通化方針（`common.js` → `api.js` → ページ固有JS）に反する。`api.js` の `api.post` を使わず直接 `fetch` を呼んでいる。

**対処案**: `common.js` または `api.js` に移動する。

---

### ISSUE-014: requirements.txt に bcrypt バージョン制約がない [Medium] [解決済み]

**現象**: `requirements.txt` に `passlib[bcrypt]==1.7.4` は記載があるが、`bcrypt<4.1` の制約が記載されていない。`pip install -r requirements.txt` で bcrypt 5.x がインストールされると `passlib` が動作しない。

**再現手順**: クリーン環境で `pip install -r requirements.txt` → bcrypt 5.x が入る → テスト実行で `ValueError: password cannot be longer than 72 bytes` エラー。

**対処案**: `requirements.txt` に `bcrypt<4.1` を追加する。

---

## 5. 仕様書の構造的問題

### ISSUE-015: 「認可」の仕様が未定義 [High] [解決済み]

**現象**: ARCHITECTURE.md で RBAC モデル（user/admin）と データアクセス制御表が定義されているが、これは「検討書」であり正式な仕様書ではない。SPEC_API.md には各エンドポイントの「認証: 必要/不要」は記載されたが、「誰のデータにアクセスできるか」の認可仕様が未定義。

**影響**: 実装者が認可のルールを知るには ARCHITECTURE.md を読む必要があるが、SPEC_API.md からはリンクされていない。

**対処案**: SPEC_API.md に「認可ルール」セクションを追加し、リソースごとのアクセス制御ポリシーを明文化する。

---

### ISSUE-016: SPEC_ROADMAP.md セクション 2.2 の記述がもはや「今後の作業」ではない [Low] [解決済み]

**箇所**: SPEC_ROADMAP.md セクション 2.2「勤怠管理（出勤・退勤の拡張）」

> ルーター層で `DEFAULT_USER_ID` をログインユーザーのIDに置き換え

**問題**: これは Phase 1 で既に完了している（`get_current_user_id` で解決済み）。セクション 2.2 の「既存機能への影響」は実態と乖離している。ただし機能自体（マルチユーザー勤怠の拡張）は未着手のため、セクション全体を「完了」にはできない。

---

## 6. 潜在的バグ

### ISSUE-017: auth_middleware が API の 401 レスポンスをブロックしない [Low] [解決済み]

**箇所**: `main.py` auth_middleware

```python
if not request.session.get("user_id"):
    if not path.startswith("/api/"):
        return RedirectResponse(url="/login", status_code=302)
return await call_next(request)
```

**動作**: 未認証の API リクエストはミドルウェアを素通りし、`Depends(get_current_user_id)` で 401 が返る。

**問題**: これは設計通り（二重チェック回避）だが、`get_current_user_id` を Depends に含めていないエンドポイント（ISSUE-001 の対象）はミドルウェアもスルーし、認証チェックが一切かからない状態になる。つまり ISSUE-001 + ISSUE-017 の組み合わせで、**未認証でも** ID さえ知っていればページ以外のルートで他人のデータにアクセスできてしまう。

**注**: 現時点では `get_current_user_id` を Depends に含めないエンドポイントでも `get_db` は Depends しているのでDB接続自体は動作する。ISSUE-001 の修正（全エンドポイントに user_id 依存追加）で同時に解決される。

---

### ISSUE-018: api_auth.py の /me エンドポイントにインライン import [Low] [解決済み]

**箇所**: `app/routers/api_auth.py` の `me()` 関数内

```python
@router.get("/me", response_model=LoginResponse)
def me(request: Request, db: Session = Depends(get_db)):
    from app.core.exceptions import AuthenticationError  # ← インライン import
    ...
    from app.crud import user as crud_user              # ← インライン import
```

**問題**: ファイル先頭でインポートすべき。循環参照回避が理由なら問題ないが、このファイルでは循環参照は発生しない。

---

## まとめ

### 重要度別件数

| 重要度 | 件数 | Issue番号 | 状態 |
|--------|------|-----------|------|
| Critical | 1 | 001 | 全件解決済み |
| High | 4 | 002, 007, 008, 015 | 全件解決済み |
| Medium | 7 | 003, 004, 005, 009, 010, 011, 014 | 003 以外解決済み（003 は Phase 2 対応） |
| Low | 6 | 006, 012, 013, 016, 017, 018 | 全件解決済み |
| **合計** | **18** | | **17件解決済み / 1件保留** |
