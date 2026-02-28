# ログ関連 問題点・技術的負債

> 調査対象: 設計書（`spec_log_function.md`）、実装コード、テスト
> Q&A ドキュメント: `docs/archive/spec_log_function_qa.md` / `docs/archive/spec_log_function_qa2.md`（アーカイブ済み）
>
> 作成日: 2026-02-18

---

## 1. 未実装機能（設計書に記載あり・実装なし）

### ~~1.1 バックグラウンドスキャナー（Phase 3）— 重大~~ **解決済み**

**対応**: `app/services/log_scanner.py` を新規作成。`reminder_checker.py` と同パターン（`asyncio.create_task` + `SessionLocal`）で実装。有効ソースの `polling_interval_sec` に基づく自動ポーリングが機能する。`LOG_SCANNER_ENABLED=true` で有効化。FTP/SMB の同期I/O は `asyncio.to_thread()` でスレッドプール実行。11件のテスト追加（`tests/test_log_scanner.py`）。

### 1.2 full_import モード（Phase 6）— 中

**状況**: 設計書にファイル内容の増分読取・DB保存・Webビューア・アラート連携が記載されているが、**未実装**。

- `log_entries` テーブル・モデル・CRUD・スキーマは実装済み
- ルーターエンドポイント（ファイル内容取得・ログ検索 API）は**未実装**
- `LogEntryContentResponse`, `LogEntrySearchResponse` スキーマは定義済みだが使用されていない
- `RemoteConnector.read_lines()` メソッドは実装済みだが、スキャン処理から呼ばれていない
- `scan_source()` は常に metadata_only 相当の処理（ファイルメタデータのみ収集）

**影響**: `collection_mode=full_import` を設定しても `metadata_only` と同じ動作。ログ内容の Web 閲覧不可。

### 1.3 自動クリーンアップ + ログ検索（Phase 7）— 低

**状況**: 設計書に90日経過した `log_entries` の自動削除とログ検索 API が記載されているが、**未実装**。

- `crud/log_entry.py` の `delete_old_entries()` は実装済みだが、呼び出し箇所なし
- `search_entries()`, `count_search_entries()` も実装済みだが、ルーターに未接続
- `LOG_RETENTION_DAYS` 設定は未定義

**影響**: full_import が未実装のため現時点では影響なし。full_import 実装時に合わせて対応必要。

---

## 2. デッドコード

### ~~2.1 `app/services/log_collector.py` — v1 レガシーコード~~ **解決済み**

**対応**: 削除済み。`main.py` の `start_collector` / `stop_collector` 呼び出しも削除。v1 専用の config 設定（`LOG_COLLECTOR_ENABLED`, `LOG_COLLECTOR_LOOP_INTERVAL`, `LOG_ALLOWED_PATHS`）も `app/config.py` から削除。

### ~~2.2 `tests/test_log_collector.py` — v1 用テスト~~ **解決済み**

**対応**: 削除済み（9テスト）。v2 のスキャン処理テストは `test_log_sources.py`（90件）に含まれている。

---

## 3. 実装上の問題

### ~~3.1 `scan_source()` の asyncio パターン — 中~~ **解決済み**

**対応**: `scan_source()` 内のアラート作成を同期的な `crud_alert.create_alert()` に変更。WebSocket ブロードキャストは戻り値 `alert_broadcast` で呼び出し側（ルーター/スキャナー）に委譲。ルーターの scan エンドポイントを `async def` に変更。

### ~~3.2 タイムゾーン不一致（当日フィルタ）— 中~~ **解決済み**

**対応**: `scan_source()` と `apply_default_preset()` 内の `date.today()` を `datetime.now(timezone.utc).date()` に統一。テストも UTC 日付に修正し、UTC/JST 境界テストを追加。

### ~~3.2b スキャンパフォーマンス（大量ファイルディレクトリ）— 中~~ **解決済み**

**対応**: `list_files()` に `modified_since` パラメータを追加し、コネクタ内部で早期フィルタリング。FTP は MLSD をジェネレータとしてイテレート（`list()` せずメモリ節約）。SMB は `fnmatch` を `is_file()`/`stat()` より先にチェック（不要なネットワークラウンドトリップ回避）。パスごとのタイムアウト制御（`LOG_SCAN_PATH_TIMEOUT`、デフォルト300秒）を追加。パスレベルのエラー隔離により、1パスの失敗が他パスのスキャンを止めない。

### 3.3 `FTPConnector.read_timeout` 未使用 — 低

**ファイル**: `app/services/remote_connector.py`

**問題**: コンストラクタで `read_timeout` を受け取るが、`ftplib.FTP` に渡していない。`connect_timeout` のみ適用されている。

### 3.4 `FTPConnector.read_lines()` メモリ問題 — 低

**ファイル**: `app/services/remote_connector.py`

**問題**: `retrbinary` でファイル全体を `BytesIO` にダウンロードしてからデコード。大きなログファイル（100MB超）でメモリ消費が問題になる可能性。

**推奨**: full_import 実装時にストリーミング読取に変更。

### 3.5 `SMBConnector.disconnect()` が no-op — 低

**ファイル**: `app/services/remote_connector.py`

**問題**: `disconnect()` が空実装（コメント: "smbprotocol manages connection pooling internally"）。長時間稼働時にセッションが蓄積する可能性。

---

## 4. テストのギャップ

### 4.1 テストカバレッジの不足

| テスト対象 | 現状 | 不足 |
|-----------|------|------|
| ファイル一覧 API | 空リスト + 404 のみ | ファイルレコードありの場合、`status` フィルタ未テスト |
| CASCADE 削除 | 未テスト | ソース削除 → パス・ファイル連動削除の検証なし |
| エンコーディング | 未テスト | Shift_JIS 等非 UTF-8 の読取テストなし |
| `RemoteConnector` | モックのみ | FTP/SMB の実接続テストなし（設計書 Q12 で「テストサーバー後日提供」） |
| `POST /api/logs/` 認証不要 | 暗黙的 | セッションなしでの POST 成功を明示テストしていない |
| ログ順序 | 未テスト | `received_at DESC` の並び順検証なし |
| ~~`log_collector.py`~~ | ~~v1 用 9件~~ | ~~v2 コードに対応していない~~ — **削除済み** |

### 4.2 テスト数の現状

| ファイル | テスト数 | 備考 |
|---------|---------|------|
| `test_log_sources.py` | 100件 | v2 対応。モック使用 |
| `test_logs.py` | 7件 | 外部ログ投入 API |

---

## 5. ドキュメントの不整合

### ~~以下の不整合は修正済み~~

| 箇所 | 問題 | 対応 |
|------|------|------|
| `docs/spec_log_function.md` Phase 3 | 状態表記が曖昧 | Phase 3 に手動スキャン実装済みの注記追加。Phase 4 にスキャン・alert_on_change・当日フィルタを含める |
| `docs/spec_log_function.md` 5章 | 設計のみで未実装 | セクション冒頭に実装状況の注記（未実装、手動スキャンのみ、v1 削除済み）追加 |
| `docs/spec_log_function.md` 設定 | config.py に未定義の設定が記載 | 状態列を追加（実装済み/未実装を明記）。v1 設定は削除済みの注記追加 |
| `docs/spec_log_function.md` 2.3, 14章 | ファイル一覧が実態と乖離 | レイヤー構成とファイル一覧を実装状態込みで更新 |
| `docs/spec_nonfunction.md` | テスト対象説明の更新漏れ | test_log_sources の説明にスキャン + アラート連携 + フォルダリンクを追加。test_log_collector（9件）を削除。合計 557件に更新 |

---

## 6. 優先度別サマリー

### ~~重大（機能が期待通り動作しない）~~ **全件解決済み**

1. ~~**バックグラウンドスキャナー未実装**~~ — **解決済み**（`log_scanner.py` 実装、`polling_interval_sec` で自動ポーリング）

### 中（機能制限・品質リスク）

2. **full_import モード未実装** — 設定しても metadata_only と同じ動作
3. ~~**asyncio パターンが脆弱**~~ — **解決済み**（同期 `crud_alert.create_alert()` + 呼び出し側ブロードキャスト）
4. ~~**タイムゾーン不一致**~~ — **解決済み**（`date.today()` → `datetime.now(timezone.utc).date()` に統一）

### 低（将来の技術的負債）

5. ~~**v1 デッドコード残存**~~ — **解決済み**（削除完了）
6. **テストカバレッジ不足** — ファイル一覧フィルタ、CASCADE 削除、エンコーディング
7. **未使用スキーマ** — `LogEntryContentResponse`, `LogEntrySearchResponse`
8. **FTP read_timeout 未適用**
9. **大ファイルのメモリ問題**（full_import 実装時に顕在化）

### ドキュメント

10. ~~**ドキュメントの不整合**~~ — **解決済み**（Phase状態、設定値、ファイル一覧、テスト数を修正）
