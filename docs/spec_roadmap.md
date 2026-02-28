# 追加機能ロードマップ

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。
> 実装済み機能の一覧と、今後の作業計画をまとめたものです。
>
> 最終更新: 2026-02-26

---

## 1. 実装済み機能一覧

全機能が実装済みであり、692件のテスト（portal_core 151件 + アプリ 541件）でカバーされている。

| # | 機能カテゴリ | 機能名 | 概要 | 状態 |
|---|-------------|--------|------|------|
| 1 | 認証 | ログイン機能 | セッションベース認証（メール+パスワード） | **実装済み** |
| 2 | 認証 | 認証セキュリティ強化 | パスワードポリシー、レート制限、アカウントロックアウト、監査ログ | **実装済み** |
| 3 | 認証 | OAuth2/SSO | Google/GitHub連携、PKCE、アカウントリンク | **実装済み** |
| 4 | 認証 | パスワードリセット | トークンベース、SMTP送信 | **実装済み** |
| 5 | ユーザー管理 | ユーザー CRUD + RBAC | admin/user ロール、グループ管理 | **実装済み** |
| 6 | 勤怠管理 | 出勤・退勤・休憩 | マルチユーザー、プリセット、Excelエクスポート、手動入力 | **実装済み** |
| 7 | 勤怠管理 | 在籍記録 | リアルタイム在籍状態（WebSocket）、Backlogチケット表示 | **実装済み** |
| 8 | Todo管理 | プライベート/公開Todo | visibility制御、公開一覧 | **実装済み** |
| 9 | タスク管理 | タスクタイマー | タイマー計測、Done時日報自動作成、一括完了 | **実装済み** |
| 10 | タスク管理 | タスクリスト | バックログ管理、担当割り当て、Task連携、時間蓄積 | **実装済み** |
| 11 | タスク管理 | タスク分類 | カテゴリマスタ管理（admin） | **実装済み** |
| 12 | 日報管理 | 日報登録 | カテゴリ、作業時間、Backlogチケット対応 | **実装済み** |
| 13 | 日報管理 | 業務サマリー | 日次/週次/月次集計、カテゴリ別分析、グループフィルタ | **実装済み** |
| 14 | ログ管理 | ログ収集 | 外部API受信 + リモートサーバー収集（FTP/SMB） | **実装済み** |
| 15 | ログ管理 | バックグラウンドスキャナー | 自動ポーリング、ファイル変更通知、フォルダリンク | **実装済み** |
| 16 | アラート管理 | アラート + ルールエンジン | 条件マッチング、WebSocket通知、ナビバッジ | **実装済み** |
| 17 | カレンダー | イベント管理 | CRUD、繰り返し、参加者、会議室予約、リマインダー | **実装済み** |
| 18 | サイトリンク | サイト監視 | URL登録、バックグラウンドヘルスチェック、WebSocket更新 | **実装済み** |
| 19 | 基盤 | portal_core分離 | 認証・ユーザー管理を再利用可能パッケージとして分離 | **実装済み** |
| 20 | 基盤 | 国際化 (i18n) | ja/en切替、gettext + JSON翻訳 | **実装済み** |
| 21 | 基盤 | テンプレート重複解消 | portal_core テンプレートをマスター化、`app_title` 動的注入、`register_head_script()` API、アプリ側重複5ファイル削除 | **実装済み** |
| 22 | Wiki管理 | Wikiページ | Markdown編集（Toast UI Editor）、階層構造、タグ/カテゴリ、タスクリンク、ファイルパスコピー | **実装済み** |

### 1.1 機能依存関係

```
[portal_core（共通基盤）]
    ├── 認証（セッション + OAuth2 + パスワードリセット）
    ├── ユーザー管理（CRUD + RBAC + グループ）
    └── WebSocket基盤 / i18n / 暗号化
        │
        ├──→ [勤怠管理]（出勤/退勤/休憩 + プリセット + Excel）
        ├──→ [在籍記録]（WebSocket リアルタイム配信）
        ├──→ [Todo管理]（private/public）
        ├──→ [タスク管理]（タイマー + タスクリスト + 分類）
        │         └──→ [日報管理]（Task Done連携 → 自動作成）
        │                   └──→ [業務サマリー]（集計・分析）
        ├──→ [ログ管理]（API受信 + リモート収集）
        │         └──→ [アラート管理]（ルールエンジン + WebSocket通知）
        ├──→ [カレンダー]（イベント + 会議室 + リマインダー）
        ├──→ [サイトリンク]（ヘルスチェック + WebSocket更新）
        └──→ [Wiki]（Markdownページ + 階層 + タグ + タスクリンク）
```

---

## 2. 次の作業（優先度順）

### 2.1 テスト失敗の修正（6件） ✅ 修正完了

6件のテスト失敗を修正済み。651件全テストパス（portal_core 151件 + アプリ 500件）。

| # | テスト | 原因 | 修正内容 |
|---|--------|------|----------|
| 1 | `test_clock_in_after_clock_out_same_day_rejected` | `attendance_service.clock_in()` が `date.today()`（ローカル時間）を使用し、CRUD の `datetime.now(timezone.utc).date()` と不一致 | `date.today()` → `datetime.now(timezone.utc).date()` に統一（`attendance_service.py`） |
| 2 | `test_polling_interval_too_high` | テストが `polling_interval_sec=999` を使用するが、上限は3600で範囲内 | テスト値を `999` → `7200`（上限超過）に修正 |
| 3 | `test_summary_category_trends` | `date.today() - 1day` が月曜の場合、前週の日曜に該当し weekly 範囲外 | 固定日付 `date(2020, 1, 8)`（水曜）を使用し週内に収まるよう修正 |
| 4 | `test_scan_alert_reads_content` | `db_session.query(LogEntry).all()` が既存DB上の全エントリを返却 | `source_id` でフィルタするよう `LogFile` JOIN を追加 |
| 5 | `test_scan_content_parser_pattern` | 同上 | 同上 |
| 6 | `test_scan_content_read_error_isolated` | 同上 | 同上 |

### 2.2 タイムゾーン不一致の修正（残り） ✅ 修正完了

`date.today()`（ローカル時間）→ `datetime.now(timezone.utc).date()`（UTC）に統一済み。

| # | 対象 | 修正内容 |
|---|------|----------|
| 1 | `log_source_service.py` `scan_source()` | 当日フィルタの `date.today()` を UTC に統一 |
| 2 | `attendance_service.py` `apply_default_preset()` | プリセット適用時の `date.today()` を UTC に統一 |
| 3 | `test_log_sources.py` | `modified_since` アサーションを UTC に修正 + UTC/JST 境界テスト追加 |
| 4 | `test_attendances.py` | プリセットテスト3件の日付アサーションを UTC に修正 |

### 2.3 軽微な技術的負債

| # | 項目 | 優先度 | 対象ファイル |
|---|------|--------|-------------|
| 1 | FTP `read_timeout` 未適用 | 低 | `remote_connector.py` |
| 2 | FTP `read_lines()` メモリ問題 | 低 | `remote_connector.py`（full_import 実装時に対応） |
| 3 | SMB `disconnect()` が no-op | 低 | `remote_connector.py` |
| 4 | 自動クリーンアップ + ログ検索 API | 低 | crud/log_entry.py に実装済みだがルーター未接続 |
| 5 | WebSocket DI化が不完全 | 低 | 5インスタンスがサービスから直接インポート |
| 6 | 翻訳ファイルの分離 | 低 | 共通キーとアプリ固有キーが混在 |
| 7 | Tasks→Reports の暗黙的依存 | 低 | Done時の日報自動作成がサービス間直接呼び出し |
| 8 | テストカバレッジ不足 | 低 | CASCADE削除、エンコーディング、ファイル一覧フィルタ |

---

## 3. 実装済み機能の詳細

> 以下は各機能の要件・決定事項のアーカイブです。

### 3.1 ログイン機能

- メールアドレスとパスワードによるセッション認証
- `SessionMiddleware`（署名Cookie）、`passlib[bcrypt]` によるパスワードハッシュ
- 認証不要パス: `/login`, `/static/*`, `/api/auth/*`, `/api/logs/`, `/ws/*`
- 設計書: [api/auth/security_enhancement.md](./api/auth/security_enhancement.md)

### 3.2 認証セキュリティ強化

- パスワードポリシー（最小8文字、大文字/小文字/数字必須）
- ログインレート制限（15分間に5回失敗でブロック）
- アカウントロックアウト（30分ロック、管理者アンロック可）
- セッション無効化（パスワード変更/ロール変更時）
- 認証監査ログ（`auth_audit_logs` テーブル）
- 設計書: [api/auth/security_enhancement.md](./api/auth/security_enhancement.md)

### 3.3 OAuth2/SSO

- Authorization Code + PKCE フロー
- Google/GitHub プロバイダ対応
- メールアドレスによる既存アカウントとの自動リンク
- プロバイダ管理（admin CRUD）、アカウントリンク/アンリンク
- 設計書: [api/auth/oauth.md](./api/auth/oauth.md)

### 3.4 パスワードリセット

- トークンベース（SHA-256ハッシュのみDB保存）
- SMTP送信、レート制限（15分間に3回まで）
- リセット成功時にセッション・全トークン無効化
- 設計書: [api/auth/password_reset.md](./api/auth/password_reset.md)

### 3.5 ログファイル収集

- リモートサーバー（FTP/SMB）からのファイルメタデータ収集
- バックグラウンドスキャナー（`LOG_SCANNER_ENABLED=true`）
- ファイル変更通知（`alert_on_change`）、フォルダリンク表示
- 認証情報の暗号化保存（Fernet）
- 設計書: [spec_log_function.md](./spec_log_function.md)
- 技術的負債: [spec_log_problem.md](./spec_log_problem.md)

### 3.6 タスクリスト

- バックログ管理: タイトル、説明、予定日、カテゴリ、Backlogチケット
- 担当割り当て/解除（Assign/Unassign）
- Start: TaskListItem → Task コピー、時間蓄積（Done時に蓄積）
- Todo はナビ非表示（URLアクセスは維持）

### 3.7 カレンダー

- FullCalendar 連携、イベント CRUD
- 繰り返しルール（RRULE形式）、例外管理
- 参加者管理（accept/decline/tentative）
- 会議室予約、空き状況確認
- リマインダー設定
- ユーザー個別設定（デフォルト表示、色、勤務時間）

### 3.8 サイトリンク

- サイトURL登録、グループ管理
- バックグラウンドヘルスチェック（`SITE_CHECKER_ENABLED=true`）
- WebSocket (`/ws/sites`) でリアルタイム更新
- SSL証明書検証、チェック間隔・タイムアウト設定
- 設計書: [api/sites/SPEC_sites.md](./api/sites/SPEC_sites.md)

### 3.9 portal_core 分離

- 認証・ユーザー管理・グループ管理を `portal_core/` パッケージに分離
- PortalApp ファクトリパターン（`setup_core()` → `register_*()` → `build()`）
- 再エクスポートshimで後方互換維持
- テスト分離（portal_core 151件 + アプリ 541件 = 692件）
- 設計書: [spec_common_separation.md](./spec_common_separation.md)

### 3.11 Wiki管理

- **エディタ**: Toast UI Editor（WYSIWYG + Markdownモード切替）
- **コンテンツ形式**: Markdown テキスト（`wiki_pages.content`: TEXT型）
- **階層構造**: `parent_id` 自己参照による親子ページ管理、パンくずナビ
- **タグ管理**: 多対多（`wiki_page_tags` 中間テーブル）、タグ名検索対応
- **カテゴリ管理**: 単一分類（管理者操作）
- **全文検索**: PostgreSQL TSVECTOR + GINインデックス（タイトル対象）
- **タスクリンク**: タスクリストアイテムへの永続リンク（`wiki_page_task_items`）、進行中タスクリンク（`wiki_page_tasks`、タイトルスナップショット付き）
- **ファイルパスコピー機能**: エディタのツールバーからUNCパス等をページに挿入、ビューアーでクリックするとクリップボードにコピー（バッジ＋フォルダアイコン表示）
- **公開範囲**: internal / public / private の3段階visibility制御
- **ページ移動**: 親ページ変更（循環参照防止チェック）
- **テスト**: 41件（`tests/test_wiki.py`）
- **DB**: wiki_pages, wiki_categories, wiki_tags, wiki_page_tags, wiki_page_task_items, wiki_page_tasks（計6テーブル）
- 設計書（旧計画）: [spec_wiki.md](./spec_wiki.md)

### 3.10 テンプレート重複解消

- portal_core テンプレート5ファイルをマスター化（`base.html`, `login.html`, `forgot_password.html`, `reset_password.html`, `users.html`）
- ハードコードの `Portal` / `Todo List Portal` を `{{ app_title }}` に動的化（`PortalApp._render()` で自動注入）
- `register_head_script()` API 追加（`app_common.js` 等のアプリ固有グローバルスクリプトを portal_core base.html に自動ループ挿入）
- アプリ側の重複5テンプレートを削除、子テンプレート14ファイルのタイトルを `{{ app_title }}` に統一

---

## 4. portal_core 拡張指針（マルチアプリ対応）

> 倉庫システム等の別アプリでも portal_core を共通基盤として利用できるよう拡張する方針。
> 既存の Todo List Portal との後方互換を維持しつつ、ロール・メニュー・権限を柔軟に構成可能にする。

### 4.1 現状の拡張ポイント（強み）

portal_core は既に以下の拡張メカニズムを備えている:

| メカニズム | 説明 |
|-----------|------|
| `PortalApp.register_router()` | アプリ固有 API ルーターの動的登録 |
| `PortalApp.register_nav_item()` | ナビゲーション項目の動的登録（`sort_order`, `hidden`, `badge_id`） |
| `PortalApp.register_page()` | HTML ページルートの動的登録 |
| `PortalApp.register_head_script()` | アプリ固有グローバルスクリプトの登録 |
| `PortalApp.register_websocket()` | WebSocket エンドポイントの動的登録 |
| `PortalApp.register_public_prefix()` | 認証バイパスパスの動的登録 |
| テンプレートオーバーライド | アプリ側 `templates/` が portal_core より優先 |
| `CoreConfig` → `AppConfig` 継承 | アプリ固有設定の追加 |
| `register_seed_hook()` | アプリ固有 DB 初期データの投入 |
| `register_startup_hook()` / `shutdown_hook()` | バックグラウンドサービスの起動・停止 |

### 4.2 現状の制約

| 制約 | 詳細 |
|------|------|
| **ロールが2種固定** | `UserRole.ADMIN` / `UserRole.USER` のみ。`require_admin` DI で二値判定 |
| **権限モデルがない** | ロールに紐づくパーミッション定義がなく、リソース単位のアクセス制御ができない |
| **ナビの権限フィルタがない** | `NavItem` は全ユーザーに同じメニューを表示（`hidden` は静的） |
| **アプリ識別がない** | ユーザーがどのアプリにアクセス可能かの概念がない |
| **認証ミドルウェアが固定** | リダイレクト先 `/login`、公開パスが factory 内にハードコード |

### 4.3 拡張方針（フェーズ案）

#### Phase A: ロール拡張 + パーミッション基盤

**目標:** `admin` / `user` の2値を超え、アプリごとにカスタムロールを定義可能にする。

**方針:**

1. **ロールレジストリ** — `core/constants.py` のハードコードを廃止し、起動時にアプリがロールを登録

```python
# 倉庫システムの例
portal.register_role("warehouse_admin", display_name="倉庫管理者", inherits=["user"])
portal.register_role("warehouse_operator", display_name="倉庫オペレーター", inherits=["user"])
portal.register_role("viewer", display_name="閲覧のみ")
```

2. **パーミッションチェッカー** — `require_admin` を汎用化

```python
# 現状: require_admin（admin/userの二値）
@router.delete("/{id}")
def delete(id: int, user_id: int = Depends(require_admin)):
    ...

# 拡張後: require_permission（リソース + アクション）
@router.delete("/{id}")
def delete(id: int, user_id: int = Depends(require_permission("users", "delete"))):
    ...
```

3. **DB テーブル追加案**

```
roles (id, name, display_name, is_system, sort_order)
role_permissions (id, role_id FK, resource, action)
user_roles (id, user_id FK, role_id FK)  -- 多対多（1ユーザーに複数ロール可）
```

4. **既存システムとの互換性** — `users.role` カラムは維持し、`user_roles` テーブルを併用。マイグレーション時に `admin` → `roles` テーブルの `admin` レコードに紐付け。`require_admin` は `require_permission("*", "*")` のエイリアスとして動作。

#### Phase B: ナビゲーション権限フィルタ

**目標:** ユーザーのロール/権限に基づいてナビメニューを動的にフィルタリング。

**方針:**

1. `NavItem` に `required_permission` 属性を追加

```python
NavItem("Users", "/users", "bi-people-fill",
        sort_order=900,
        required_permission="users:read")  # この権限がないユーザーには非表示
```

2. `_render()` でリクエストユーザーの権限を取得し、`nav_items` をフィルタして渡す

3. 権限なしの `NavItem` は全ユーザーに表示（後方互換）

#### Phase C: マルチアプリ識別（将来）

**目標:** 1つの portal_core インスタンスで複数アプリを区別して管理。

**方針（検討段階）:**

- `apps` テーブル（`id`, `name`, `slug`）でアプリを識別
- `user_app_access` テーブルでユーザーのアプリアクセス権を管理
- ナビバーにアプリ切替メニューを追加
- ルーターにアプリスコープのプレフィックスを付与

> この Phase は倉庫システムの要件が具体化してから設計を詰める。
> 当面は Phase A・B で十分な拡張性を確保できる見込み。

### 4.4 倉庫システム向けの想定ロール例

| ロール | 権限概要 | 既存互換 |
|--------|---------|---------|
| `admin` | 全操作（ユーザー管理、マスタ管理、設定変更） | 既存 `admin` と同一 |
| `warehouse_admin` | 倉庫マスタ管理 + 入出庫承認 + レポート閲覧 | 新規 |
| `warehouse_operator` | 入出庫登録 + 在庫照会 | 新規 |
| `viewer` | 閲覧のみ（レポート、在庫状況） | 新規 |
| `user` | Todo/タスク/日報等の一般操作（既存アプリ機能） | 既存 `user` と同一 |

### 4.5 既存 Todo List Portal への影響

| 変更 | 後方互換 |
|------|---------|
| `users.role` カラム維持 | ✅ 既存のまま動作 |
| `require_admin` → `require_permission` エイリアス | ✅ `require_admin` はそのまま使用可能 |
| `NavItem` に `required_permission` 追加 | ✅ 未指定なら全ユーザーに表示 |
| `roles` / `role_permissions` テーブル追加 | ✅ 既存テーブルに影響なし |
| `user_roles` テーブル追加 | ✅ マイグレーションで既存ユーザーを自動紐付け |

---

## 5. 画面一覧

| 画面名 | パス | 提供元 |
|--------|------|--------|
| ログイン | `/login` | portal_core |
| パスワードリセット要求 | `/forgot-password` | portal_core |
| パスワード再設定 | `/reset-password` | portal_core |
| ユーザー管理 | `/users` | portal_core |
| Dashboard | `/` | アプリ |
| Todo | `/todos` | アプリ（ナビ非表示） |
| 公開Todo一覧 | `/todos/public` | アプリ（ナビ非表示） |
| タスクリスト | `/task-list` | アプリ |
| 勤怠管理 | `/attendance` | アプリ |
| 在籍状態 | `/presence` | アプリ |
| タスク | `/tasks` | アプリ |
| 日報 | `/reports`, `/reports/{id}` | アプリ |
| 業務サマリー | `/summary` | アプリ |
| カレンダー | `/calendar` | アプリ |
| サイトリンク | `/sites` | アプリ |
| Wiki一覧 | `/wiki` | アプリ |
| Wiki新規作成 | `/wiki/new` | アプリ |
| Wikiページ閲覧 | `/wiki/{slug}` | アプリ |
| Wikiページ編集 | `/wiki/{slug}/edit` | アプリ |
| ログ | `/logs` | アプリ |
| アラート | `/alerts` | アプリ |
