# Question5: 現時点の疑問点・確認事項

**作成日**: 2026-02-16

---

## 1. 設計判断が必要な事項

### Q5-01: `password_hash` を nullable のままにすべきか？

**背景**: `app/models/user.py` で `password_hash = Column(String(255), nullable=True)`。ISSUE4-2.5 で課題として記載。

**現状**: OAuth2/SSO が実装済みのため、OAuth のみでログインするユーザーはローカルパスワードを持たない。`auth_service.authenticate()` は `if not user.password_hash` で事前チェック済み。

**選択肢**:
- A) nullable のまま維持（OAuth-only ユーザーに対応）
- B) NOT NULL に変更しランダムハッシュを埋める（OAuth ユーザーもローカルパスワード必須）

**質問**: OAuth-only ユーザーを許容する設計で良いか？

---

### Q5-02: テスト DB と本番 DB の分離は必要か？

**背景**: `tests/conftest.py` は `DATABASE_URL`（本番と同じ）を使用。テストはトランザクションロールバックで分離するが、`seed_default_user()` / `seed_default_presets()` / `seed_default_categories()` はアプリ起動時にコミットされ、テストトランザクション外。

**影響**: 本番 DB のシードデータが書き換わるリスク（低い）。stale データによるテスト失敗（1件現存）。

**選択肢**:
- A) 分離する（`TEST_DATABASE_URL` 環境変数を追加）
- B) 現状維持（小規模チームなので許容）
- C) テストモードではシード処理をスキップ

---

### Q5-03: TaskListItem のステータス遷移を制約すべきか？（ISSUE-059）

**背景**: 現在 `TaskListItemUpdate` で `status` が直接更新可能。`open → done` への直接変更（タスク作業なしで完了）や `done → open` への巻き戻しも可能。

**選択肢**:
- A) 遷移制約を追加（`open → in_progress → done` のみ許可）
- B) `status` を `TaskListItemUpdate` から除外し、アクション API（`/start`, `/done`）経由のみに制限
- C) 現状維持（運用で対応）

---

### Q5-04: `POST /api/logs/` のレート制限は何で実現すべきか？（ISSUE-069）

**背景**: 認証不要の公開エンドポイント。レート制限もフィールドサイズ制限もない。

**選択肢**:
- A) アプリケーション層で対応（SlowAPI ミドルウェア + `Field(max_length=...)` 追加）
- B) リバースプロキシ（nginx 等）で対応
- C) フィールドサイズ制限のみアプリで追加し、レート制限はプロキシに委任

---

## 2. 機能実装状況の確認

### Q5-05: Calendar / Group 機能は完成済みか？

**背景**: CLAUDE.md に「Calendar/Group models: model files + migrations exist, but NOT imported in `__init__.py` and NOT wired in `main.py`」と記載があるが、実際にはコードを確認すると**既にフル稼働している**。

**現状**:
- `app/models/__init__.py` — Calendar 全モデル・Group モデルが import 済み
- `main.py` — `api_calendar.router`, `api_groups.router` が include 済み
- テスト — `test_calendar.py`（29件）、`test_calendar_rooms.py`（18件）、`test_groups.py`（11件）が存在

**質問**: これらの機能は完成済みと見なしてよいか？CLAUDE.md の記述を更新すべきか？

---

### Q5-06: TemplateResponse の DeprecationWarning は本当に解決済みか？

**背景**: ISSUE4-3.4 で「✅ 解決済み」と記載。しかし `app/routers/pages.py` の全17ルートが依然として旧パターン（位置引数）を使用しているように見える。

```python
# 現在のコード（全ルート共通）
TemplateResponse("xxx.html", {"request": request})

# 推奨パターン
TemplateResponse(request=request, name="xxx.html")
```

テスト実行時にも6件の DeprecationWarning が出力されている。

**質問**: 対応済みなら、なぜ警告が出ているのか？Starlette のバージョンによる挙動差異か？

---

## 3. ドキュメント不整合

### Q5-07: テスト件数の記載が古い

**背景**: `docs/spec_nonfunction.md` セクション6.2 のテスト件数合計が **396件** と記載されているが、実際のテスト数は **469件**。

**差分の主要因**:
| テストファイル | 記載 | 実際 | 差 |
|---------------|------|------|-----|
| `test_attendances.py` | 52 | 62 | +10 |
| `test_task_list.py` | 32 | 34 | +2 |
| `test_summary.py` | 12 | 15 | +3 |
| `test_calendar.py` | 未記載 | 29 | +29 |
| `test_calendar_rooms.py` | 未記載 | 18 | +18 |
| `test_groups.py` | 未記載 | 11 | +11 |

**質問**: 仕様書のテスト件数を最新化すべきか？

---

### Q5-08: CLAUDE.md の Alembic ヘッド記載が古い

**背景**: CLAUDE.md では `Current head: a943bf44ce3b` と記載しているが、`db-schema.md` と一致していることを確認。ただし CLAUDE.md の migration chain に `auth_security` → `oauth` → `password_reset` が含まれていない（中途半端に更新されている）。

**確認**: CLAUDE.md の Alembic セクションの更新は別途行うべきか？

---

## 4. テスト関連

### Q5-09: `test_summary_category_trends` の常時失敗をどう対処するか？

**背景**: `tests/test_summary.py` の `test_summary_category_trends` が stale データにより常時失敗。

**原因**: テストが `date.today()` を基準日に使用するため、テストトランザクション外にコミットされた DailyReport レコードが結果に混入する。同ファイル内の他テスト（`test_user_report_status_category_breakdown` 等）は `date(2020, 1, 6)` のような過去日付を指定して回避済み。

**修正案**: 基準日を stale データのない過去日付（例: `date(2020, 7, 6)`）に変更。

**質問**: この修正を実施してよいか？

---

## 5. リファクタリング方針

### Q5-10: attendance_service の dict 返却パターンを ORM に統一すべきか？（ISSUE4-3.1 / ISSUE5-072 / ISSUE5-083）

**背景**: 3つの ISSUE が同根の問題を指摘。`Attendance` モデルに `breaks` リレーションがないため、`_attach_breaks()` で手動 dict 変換している。

**対処案**: `Attendance` モデルに `relationship("AttendanceBreak", ...)` を追加し、ORM オブジェクトのまま返す方式に変更。これにより:
- ISSUE4-3.1（返却型不統一）→ 解消
- ISSUE5-072（N+1 クエリ）→ `joinedload` で解消
- ISSUE5-083（サービス戻り値不統一）→ 部分解消

**質問**: このリファクタリングの優先度は？今実施すべきか、将来対応で良いか？

---

### Q5-11: CRUD 基底クラスの導入は行うべきか？（ISSUE5-082）

**背景**: 19の CRUD ファイルで `get_by_id`, `create`, `update`, `delete` の同一パターンが重複。基底クラス `CRUDBase[ModelType]` の導入が提案されている。

**懸念**:
- 大規模リファクタリング（全19ファイル + テスト）
- 個別 CRUD にカスタムロジックがある場合の対応
- 既存テスト（469件）への影響

**質問**: 導入する場合の段階的アプローチ（新規 CRUD から適用 → 既存を段階移行）で良いか？

---

## まとめ

| 区分 | 件数 | 番号 |
|------|------|------|
| 設計判断 | 4 | Q5-01 〜 Q5-04 |
| 機能確認 | 2 | Q5-05, Q5-06 |
| ドキュメント | 2 | Q5-07, Q5-08 |
| テスト | 1 | Q5-09 |
| リファクタリング | 2 | Q5-10, Q5-11 |
| **合計** | **11** | |
