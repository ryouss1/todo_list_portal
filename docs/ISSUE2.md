# 仕様・実装 Issue 一覧 (Phase 7-8 完了時点)

> Phase 7（ログファイル収集）・Phase 8（システムアラート）完了時点での仕様書・実装の問題点を整理したもの。
> [ISSUE.md](./ISSUE.md) の続編。ISSUE.md で解決済みの課題は含まない。
> 重要度: **Critical** > **High** > **Medium** > **Low**

---

## 1. セキュリティ

### ISSUE-019: WebSocket 3エンドポイントが全て認証不要 [High] [解決済み]

**現象**: `/ws/logs`, `/ws/presence`, `/ws/alerts` の全WebSocketエンドポイントが認証なしで接続可能。

**対処**: WebSocket接続後にセッションCookieから`user_id`を読み取り、未認証の場合はcode=4401で切断するよう実装。`_ws_get_user_id()` ヘルパーを追加。テストに未認証接続拒否テストを追加。

---

### ISSUE-020: CSRF対策が未実装 [High] [解決済み]

**現象**: セッションベース認証を使用しているが、CSRF トークン検証が一切ない。

**対処**: `csrf_middleware` を追加。POST/PUT/PATCH/DELETE リクエストで Origin/Referer ヘッダーを検証し、ホスト不一致の場合は403を返す。非ブラウザクライアント（Origin/Referer なし）は許可。

---

### ISSUE-021: LogSource の file_path にパス検証がない [High] [解決済み]

**現象**: `LogSourceCreate` スキーマの `file_path` フィールドにパス検証がない。

**対処**: `_validate_file_path()` バリデーターを追加。絶対パス必須、`..` 禁止、`LOG_ALLOWED_PATHS` 環境変数によるホワイトリスト制限。Create/Update 両スキーマに適用。

---

### ISSUE-022: ログ API (`/api/logs/*`) が認証不要 [Medium] [解決済み]

**現象**: ログの作成・閲覧が認証なしで可能。

**対処**: GET `/api/logs/` と GET `/api/logs/important` に `Depends(get_current_user_id)` を追加し認証必須に。POST `/api/logs/` は外部ログ取り込み用として認証不要を維持。

---

### ISSUE-023: アラートルール・ログソースにRBAC（権限制御）がない [Medium] [解決済み]

**現象**: 認証済みユーザーであれば誰でもアラートルール・ログソースの作成・変更・削除が可能。

**対処**: `users.role` カラム追加（default "user"）、`require_admin` 依存関数を追加。ログソース・アラートルールの POST/PUT/DELETE を admin 限定に。GET は全認証ユーザーに許可。

---

### ISSUE-024: ユーザー作成APIに管理者チェックがない [Medium] [解決済み]

**現象**: `POST /api/users/` は認証のみ必須で、任意の認証済みユーザーが新規ユーザーを作成可能。

**対処**: `POST /api/users/` に `Depends(require_admin)` を適用。管理者のみユーザー作成可能。

---

## 2. 仕様書の記述問題

### ISSUE-025: SPEC_ROADMAP.md の Phase 2 WebSocket認証記述が曖昧 [Medium] [解決済み]

**対処**: 「Phase 2で対応予定」を「将来検討: トークン認証等の導入」に修正。

---

### ISSUE-026: alert の severity 値が logs と alerts で体系が異なる [Medium] [解決済み]

**対処（文書化）**: SPEC_DB.md にアラート severity 値一覧と、ログ severity との違いに関する注記を追加。

**対処（バリデーション）**: `AlertSeverity = Literal["info", "warning", "critical"]` を導入し、AlertCreate/AlertRuleCreate/Update の severity フィールドに適用。不正値は422で拒否。

---

### ISSUE-027: SPEC_DB.md の todos.visibility カラムが記載されていない [Low] [解決済み]

**対処**: SPEC_DB.md の todos テーブル定義に visibility カラムと値一覧を追加。

---

### ISSUE-028: CLAUDE.md の Alembic head 記述が二箇所で矛盾 [Low] [解決済み]

**対処**: migration chain にリビジョンハッシュ付きで全ステップを明記。

---

### ISSUE-029: dev-workflow SKILL.md と MEMORY.md のテスト数が古い [Low] [解決済み]

**対処**: dev-workflow SKILL.md のテスト数を更新。

---

## 3. アーキテクチャ上の問題

### ISSUE-030: ログコレクターのグローバルシングルトンタスク [Medium] [解決済み]

**対処**: `app.state.collector_task` でタスク管理。モジュールグローバル `_collector_task` を廃止。

---

### ISSUE-031: base.html のアラートバッジが `api.js` を使わず直接 `fetch` [Low] [解決済み]

**対処**: `fetch('/api/alerts/count')` を `api.get('/api/alerts/count')` に変更。

---

### ISSUE-032: alert_service の同期/非同期混在 [Low] [解決済み]

**対処**: `alert_service.py` の全パブリック関数を `async` に統一。

---

## 4. テストの考慮不足

### ISSUE-033: アラートルール・ログソースの認可テストがない [High] [解決済み]

**対処**: TestLogSourceRBAC、TestAlertRuleRBAC、TestAlertRBAC、TestUserRBAC テストクラスを追加。非admin ユーザーの作成・更新・削除拒否（403）と読み取り許可（200）を検証。

---

### ISSUE-034: パストラバーサルのテストがない [High] [解決済み]

**対処**: TestLogSourcePathValidation テストクラスを追加。相対パス拒否、パストラバーサル拒否、更新時のパス検証を検証。

---

### ISSUE-035: severity 値の境界テストがない [Medium] [解決済み]

**対処**: TestAlertSeverityValidation、TestAlertRuleSeverityValidation テストクラスを追加。不正値・空文字・大文字混在の拒否と有効値の受理を検証。

---

### ISSUE-036: ログ経由のアラート大量生成テストがない [Medium] [解決済み]

**対処**: `test_multiple_rules_match_same_log` テストを追加。複数ルールが同一ログにマッチした場合の複数アラート生成を検証。

---

### ISSUE-037: WebSocket認証のテストがない [Medium] [解決済み]

**対処**: `test_websocket_unauthenticated_disconnect` テストを追加。未認証 WebSocket 接続がcode=4401で切断されることを検証。認証済みテストはログイン後にWebSocket接続するよう更新。

---

## 5. 潜在的バグ

### ISSUE-038: ログコレクターの collect_from_source が部分書き込み行を読む可能性 [Medium] [解決済み]

**対処**: `read_new_lines()` を行単位読み取りに変更。最終行が改行で終わっていない場合は読み取らず、位置を行頭に保持して次回ポーリングに持ち越し。`test_partial_line_held_back` テストを追加。

---

### ISSUE-039: アラートルール condition の JSON 型検証が不十分 [Medium] [解決済み]

**対処**: `_validate_condition()` バリデーターを追加。空条件禁止、未知演算子検出（`$in`/`$contains` のみ許可）、リスト値拒否。TestAlertRuleConditionValidation テストクラスを追加。

---

### ISSUE-040: `_safe_format_map` で format string injection のリスク [Low] [解決済み]

**対処**: `str.format_map` + `SafeDict` を `string.Template.safe_substitute` に置換。`{variable}` 構文を `${variable}` に変換して Template で安全に展開。属性アクセスやメソッド呼び出しのリスクを排除。

---

## 6. 運用上の問題

### ISSUE-041: LOG_COLLECTOR_ENABLED のデフォルトが true [Low] [解決済み]

**対処**: `LOG_COLLECTOR_ENABLED` のデフォルトを `"false"` に変更。ログソースを使用する場合は明示的に有効化が必要。

---

### ISSUE-042: アラートの削除APIがない [Low] [解決済み]

**対処**: `DELETE /api/alerts/{id}` エンドポイントを追加（admin 限定）。CRUD層に `delete_alert`、サービス層に `delete_alert` を追加。テストに `test_delete_alert` と `test_delete_alert_not_found` を追加。

---

## まとめ

### 重要度別件数

| 重要度 | 件数 | 未解決 | Issue番号 |
|--------|------|--------|-----------|
| High | 5 | 0 | ~~019~~, ~~020~~, ~~021~~, ~~033~~, ~~034~~ |
| Medium | 11 | 0 | ~~022~~, ~~023~~, ~~024~~, ~~025~~, ~~026~~, ~~030~~, ~~035~~, ~~036~~, ~~037~~, ~~038~~, ~~039~~ |
| Low | 8 | 0 | ~~027~~, ~~028~~, ~~029~~, ~~031~~, ~~032~~, ~~040~~, ~~041~~, ~~042~~ |
| **合計** | **24** | **0** | **全24件解決済み** |

### カテゴリ別件数

| カテゴリ | 件数 | 解決済み |
|---------|------|---------|
| セキュリティ | 6 (019-024) | 6件解決 |
| 仕様書の記述問題 | 5 (025-029) | 5件解決 |
| アーキテクチャ | 3 (030-032) | 3件解決 |
| テストの考慮不足 | 5 (033-037) | 5件解決 |
| 潜在的バグ | 3 (038-040) | 3件解決 |
| 運用上の問題 | 2 (041-042) | 2件解決 |
