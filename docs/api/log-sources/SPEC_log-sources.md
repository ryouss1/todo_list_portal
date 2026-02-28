# Log Source 機能仕様書

> リモートサーバー（FTP/SMB）からのファイルベースログ収集機能の完全な仕様。
> ログソース管理・接続テスト・スキャン・バックグラウンド自動収集・ファイル変更通知を含む。

---

## 1. 概要

### 1.1 背景

外部サーバー上にあるログファイルを定期的に取得・管理する機能。
直接ファイルアクセスできない環境（リモートサーバー上の IIS/Apache ログ等）を対象とし、
FTP または SMB（Windows 共有フォルダー）経由でファイルメタデータまたはコンテンツを収集する。

> **v1 との違い**: v1 はローカルファイルパス直接読み取り方式。v2（現行）はリモートサーバー接続方式。

### 1.2 目的

- FTP/SMB 経由でリモートサーバーのログファイルメタデータを定期収集
- ファイル変更（新規・更新）検出時のアラート自動生成
- `full_import` モードでログファイルの内容を `log_entries` テーブルに取り込み
- バックグラウンドスキャナーによる自動ポーリング
- 管理者 UI からの手動スキャン・接続テスト

### 1.3 主要コンポーネント

| コンポーネント | 役割 |
|-------------|------|
| `LogSource` | リモートサーバー接続情報・収集設定の定義 |
| `LogSourcePath` | 1 ソースに対して複数の監視パス（ディレクトリ）を管理 |
| `LogFile` | スキャンで検出されたファイルのメタデータ管理 |
| `LogEntry` | `full_import` で取り込んだログ行データ |
| `RemoteConnector` | FTP/SMB 接続の抽象インターフェース |
| `LogScanner` | バックグラウンド自動スキャンタスク |

### 1.4 基本フロー

```
[手動スキャン] POST /api/log-sources/{id}/scan
[自動スキャン] LogScanner (バックグラウンド)
        ↓
scan_source(db, source_id)
        ↓
RemoteConnector (FTP/SMB).list_files(base_path, file_pattern, modified_since=today)
        ↓
ファイルメタデータ比較（サイズ・更新日時）→ new / updated / unchanged
        ↓
crud_log_file.upsert_file() → log_files テーブル更新
        ↓
[full_import + alert_on_change の場合] ファイル内容読み取り → log_entries 保存
        ↓
[alert_on_change + 変更あり] アラート生成 → WebSocket ブロードキャスト
```

---

## 2. データモデル

### 2.1 log_sources テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK, AUTO | ソースID |
| name | String(200) | NOT NULL | ソース表示名 |
| group_id | Integer | FK(groups.id), NOT NULL | 所属グループID |
| access_method | String(10) | NOT NULL | 接続方式（`ftp` / `smb`） |
| host | String(255) | NOT NULL | 接続先ホスト名/IPアドレス |
| port | Integer | NULL許可 | ポート番号（NULL=デフォルト: FTP=21, SMB=445） |
| username | String(500) | NOT NULL | ユーザー名（**Fernet暗号化保存**） |
| password | String(500) | NOT NULL | パスワード（**Fernet暗号化保存**） |
| domain | String(200) | NULL許可 | SMBドメイン（SMB接続時のみ） |
| encoding | String(20) | NOT NULL, server_default `utf-8` | ファイルエンコーディング |
| source_type | String(20) | NOT NULL, server_default `OTHER` | ソース種別 |
| polling_interval_sec | Integer | NOT NULL, default 60 | ポーリング間隔（秒、60〜3600） |
| collection_mode | String(20) | NOT NULL, server_default `metadata_only` | 収集モード |
| parser_pattern | Text | NULL許可 | 正規表現（`full_import` 時のみ使用） |
| severity_field | String(100) | NULL許可 | severity を抽出するグループ名 |
| default_severity | String(20) | NOT NULL, server_default `INFO` | severity 未抽出時のデフォルト |
| is_enabled | Boolean | NOT NULL, default true | 有効/無効 |
| alert_on_change | Boolean | NOT NULL, server_default false | ファイル変更時アラートフラグ |
| consecutive_errors | Integer | NOT NULL, default 0 | 連続エラー回数 |
| last_checked_at | DateTime(TZ) | NULL許可 | 最終チェック日時 |
| last_error | Text | NULL許可 | 最終エラーメッセージ |
| created_at | DateTime(TZ) | server_default now() | 作成日時 |
| updated_at | DateTime(TZ) | server_default now(), onupdate | 更新日時 |

**access_method 値:**

| 値 | 説明 | デフォルトポート |
|----|------|----------------|
| `ftp` | FTP接続 | 21 |
| `smb` | SMB/CIFS（Windows共有） | 445 |

**source_type 値:**

| 値 | 説明 |
|----|------|
| `WEB` | Webアプリケーションログ |
| `HT` | HTTPサーバー（IIS/Apache）ログ |
| `BATCH` | バッチ処理ログ |
| `OTHER` | その他 |

**collection_mode 値:**

| 値 | 説明 |
|----|------|
| `metadata_only` | ファイル名・サイズ・更新日時のみ収集。コンテンツは読まない |
| `full_import` | ファイル内容を読み取り、`log_entries` テーブルに取り込む |

### 2.2 log_source_paths テーブル

1 つの LogSource に対して複数の監視ディレクトリを持てる（1:N）。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK, AUTO | パスID |
| source_id | Integer | FK(log_sources.id, CASCADE), NOT NULL, INDEX | ソースID |
| base_path | String(1000) | NOT NULL | リモートフォルダパス |
| file_pattern | String(200) | NOT NULL, server_default `*.log` | ファイルパターン（glob形式） |
| is_enabled | Boolean | NOT NULL, default true | 有効/無効 |
| created_at | DateTime(TZ) | server_default now() | 作成日時 |
| updated_at | DateTime(TZ) | server_default now(), onupdate | 更新日時 |

### 2.3 log_files テーブル

スキャンで検出されたファイルのメタデータ管理。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK, AUTO | ファイルID |
| source_id | Integer | FK(log_sources.id, CASCADE), NOT NULL, INDEX | ソースID（集計用） |
| path_id | Integer | FK(log_source_paths.id, CASCADE), NOT NULL, INDEX | パスID |
| file_name | String(500) | NOT NULL | ファイル名 |
| file_size | BigInteger | NOT NULL, default 0 | ファイルサイズ（バイト） |
| file_modified_at | DateTime(TZ) | NULL許可 | ファイル更新日時（リモート） |
| last_read_line | Integer | NOT NULL, default 0 | 最終読込行番号（`full_import` 差分取込用） |
| status | String(20) | NOT NULL, server_default `new` | ファイルステータス |
| created_at | DateTime(TZ) | server_default now() | 作成日時 |
| updated_at | DateTime(TZ) | server_default now(), onupdate | 更新日時 |

- UNIQUE制約: `(path_id, file_name)`

**status 値:**

| 値 | 説明 |
|----|------|
| `new` | 当日スキャンで新規検出 |
| `unchanged` | 前回から変更なし（サイズ・更新日時一致） |
| `updated` | 前回からサイズまたは更新日時が変化 |
| `deleted` | リモートには存在しない（当日リストに含まれなかった） |
| `error` | 読み取りエラー |

### 2.4 log_entries テーブル

`collection_mode=full_import` 時のみ使用。ファイルから取り込んだ行データ。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK, AUTO | エントリID |
| file_id | Integer | FK(log_files.id, CASCADE), NOT NULL, INDEX | ファイルID |
| line_number | Integer | NOT NULL | 行番号（1始まり） |
| severity | String(20) | NOT NULL, server_default `INFO` | 重要度（パーサーで抽出または default_severity） |
| message | Text | NOT NULL | ログメッセージ |
| received_at | DateTime(TZ) | server_default now() | 取込日時 |

- 複合インデックス: `(file_id, line_number)`

### 2.5 テーブル関係

```
log_sources (1) ──── (N) log_source_paths  [CASCADE]
log_source_paths (1) ──── (N) log_files    [CASCADE]
log_sources (1) ──── (N) log_files         [CASCADE, クエリ利便性のため冗長FK]
log_files (1) ──── (N) log_entries          [CASCADE]
groups (1) ──── (N) log_sources.group_id
```

---

## 3. API エンドポイント

認証: 全エンドポイントで必要

| メソッド | パス | 認可 | 説明 | ステータス |
|---------|------|------|------|---------|
| GET | `/api/log-sources/` | 認証ユーザー | ソース一覧（全情報） | 200 |
| GET | `/api/log-sources/status` | 認証ユーザー | ステータス一覧（ダッシュボード用軽量版） | 200 |
| POST | `/api/log-sources/` | **Admin のみ** | ソース作成 | 201 / 422 |
| GET | `/api/log-sources/{id}` | 認証ユーザー | ソース詳細取得 | 200 / 404 |
| PUT | `/api/log-sources/{id}` | **Admin のみ** | ソース更新 | 200 / 404 |
| DELETE | `/api/log-sources/{id}` | **Admin のみ** | ソース削除 | 204 / 404 |
| POST | `/api/log-sources/{id}/test` | **Admin のみ** | 接続テスト | 200 / 404 |
| POST | `/api/log-sources/{id}/scan` | **Admin のみ** | スキャン実行 | 200 / 404 |
| POST | `/api/log-sources/{id}/re-read` | **Admin のみ** | コンテンツ再読込 | 200 / 404 |
| GET | `/api/log-sources/{id}/files` | 認証ユーザー | ファイル一覧 | 200 / 404 |

### 3.1 GET /api/log-sources/

全 LogSource の詳細情報（パス一覧・マスク済みユーザー名含む）を返却する。
パスワードは一切返却しない。ユーザー名は先頭1文字 + `****` にマスク。

レスポンス: `LogSourceResponse[]`

### 3.2 GET /api/log-sources/status

ダッシュボードテーブル向けの軽量レスポンス。
`has_alert=true` の場合、変更ファイルの詳細とフォルダリンクを `changed_paths` に含める。

レスポンス: `LogSourceStatusResponse[]`

### 3.3 POST /api/log-sources/

ソースを作成する。

- 認証情報（username/password）はサーバー側で Fernet 暗号化して保存
- `paths` は 1 件以上必須
- `CREDENTIAL_ENCRYPTION_KEY` が未設定の場合、`400 ConflictError` を返す

リクエストボディ: `LogSourceCreate`（詳細はセクション 4 参照）

### 3.4 PUT /api/log-sources/{id}

ソースを部分更新する（`exclude_unset=True`）。

**パス（paths）の更新ルール**:
- `id` あり → 既存パスの更新
- `id` なし → 新規パス追加
- レスポンスに含まれないパス → 削除（reconcile）

### 3.5 POST /api/log-sources/{id}/test

リモートサーバーに接続し、各パスのファイル一覧取得を試みる。

- 接続成功時: `last_checked_at` を更新
- パス単位で結果を返却（1 パスがエラーでも他のパスは継続テスト）
- 全パス成功 → `status: "ok"`, 1 件以上失敗 → `status: "error"`

レスポンス: `ConnectionTestResponse`

### 3.6 POST /api/log-sources/{id}/scan

リモートに接続し、当日（`file_modified_at.date() == today`）のファイルのみ DB に登録/更新する。

スキャン処理の詳細はセクション 5 参照。

レスポンス: `ScanResultResponse`

副作用:
- `log_files` テーブル更新（new/updated/unchanged/deleted）
- `log_source.last_checked_at` / `last_error` 更新
- `alert_on_change=True` かつ変更あり → アラート生成 + WebSocket ブロードキャスト

### 3.7 POST /api/log-sources/{id}/re-read

既存の `log_entries` を全削除し、`last_read_line` を 0 にリセットした後、スキャンを再実行する。

用途: エンコーディング変更後にコンテンツを正しく再取得する。

処理手順:
1. 対象ソースの全 `log_entries` を削除
2. 全 `log_files.last_read_line` を 0 にリセット
3. `scan_source()` を実行（通常スキャンと同じ）

レスポンス: `ScanResultResponse`（scan_source と同形式）

### 3.8 GET /api/log-sources/{id}/files

ソースに紐づく `log_files` の一覧を返却する。

クエリパラメータ:
- `status` (任意): ファイルステータスフィルタ（`new` / `updated` / `unchanged` 等）

---

## 4. スキーマ定義

### 4.1 LogSourceCreate

| フィールド | 型 | デフォルト | 必須 | バリデーション |
|-----------|-----|----------|------|-------------|
| name | str | - | Yes | - |
| group_id | int | - | Yes | - |
| access_method | str | - | Yes | `ftp` または `smb` のみ |
| host | str | - | Yes | - |
| port | int | null | No | - |
| username | str | - | Yes | - |
| password | str | - | Yes | - |
| domain | str | null | No | SMB のみ使用 |
| paths | LogSourcePathCreate[] | - | Yes | 1 件以上必須 |
| encoding | str | `utf-8` | No | - |
| source_type | str | `OTHER` | No | `WEB`/`HT`/`BATCH`/`OTHER` のいずれか |
| polling_interval_sec | int | 60 | No | 60〜3600 の範囲 |
| collection_mode | str | `metadata_only` | No | `metadata_only` または `full_import` のみ |
| parser_pattern | str | null | No | 有効な正規表現であること |
| severity_field | str | null | No | - |
| default_severity | str | `INFO` | No | - |
| is_enabled | bool | true | No | - |
| alert_on_change | bool | false | No | - |

### 4.2 LogSourcePathCreate / LogSourcePathUpdate

| フィールド | 型 | デフォルト | 必須 | 説明 |
|-----------|-----|----------|------|------|
| id | int | null | No（Update のみ） | 既存パスID（ある場合は更新、ない場合は新規作成） |
| base_path | str | - | Yes | リモートフォルダパス |
| file_pattern | str | `*.log` | No | glob パターン（例: `*.log`, `access_*.log`） |
| is_enabled | bool | true | No | - |

### 4.3 LogSourceUpdate

全フィールド Optional（部分更新）。同バリデーションルールを適用。
`paths` を送信した場合は reconcile（更新・新規追加・削除）。

### 4.4 LogSourceResponse

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | ソースID |
| name | str | ソース名 |
| group_id | int | グループID |
| group_name | str | グループ名（結合取得） |
| access_method | str | 接続方式 |
| host | str | ホスト名/IP |
| port | int\|null | ポート番号 |
| username_masked | str | マスク済みユーザー名（例: `a****`） |
| domain | str\|null | ドメイン |
| paths | LogSourcePathResponse[] | 監視パス一覧 |
| encoding | str | エンコーディング |
| source_type | str | ソース種別 |
| polling_interval_sec | int | ポーリング間隔（秒） |
| collection_mode | str | 収集モード |
| parser_pattern | str\|null | 正規表現パターン |
| severity_field | str\|null | severityグループ名 |
| default_severity | str | デフォルト severity |
| is_enabled | bool | 有効フラグ |
| alert_on_change | bool | ファイル変更通知フラグ |
| consecutive_errors | int | 連続エラー回数 |
| last_checked_at | datetime\|null | 最終チェック日時 |
| last_error | str\|null | 最終エラーメッセージ |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

> **セキュリティ**: `username` / `password` カラムの生値はレスポンスに含めない。

### 4.5 LogSourceStatusResponse

ダッシュボードテーブル用の軽量レスポンス（接続情報詳細・paths 配列なし）。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | int | ソースID |
| name | str | ソース名 |
| group_id / group_name | int / str | グループ |
| access_method | str | 接続方式 |
| host | str | ホスト名/IP |
| source_type | str | ソース種別 |
| collection_mode | str | 収集モード |
| is_enabled | bool | 有効フラグ |
| alert_on_change | bool | 変更通知フラグ |
| consecutive_errors | int | 連続エラー回数 |
| last_checked_at | datetime\|null | 最終チェック日時 |
| last_error | str\|null | 最終エラー |
| path_count | int | 監視パス数 |
| file_count | int | 管理対象ファイル総数 |
| new_file_count | int | 新規ファイル数（当日） |
| updated_file_count | int | 更新ファイル数（当日） |
| has_alert | bool | アラート状態（`alert_on_change AND is_enabled AND 変更あり`） |
| changed_paths | ChangedPathInfo[] | 変更パス詳細（has_alert=true 時のみ値あり、false 時は空配列） |

### 4.6 ChangedPathInfo

| フィールド | 型 | 説明 |
|-----------|-----|------|
| path_id | int | パスID |
| base_path | str | ベースパス |
| folder_link | str | フォルダリンクURL（SMB: `file:////host/path/`、FTP: `ftp://host/path/`） |
| copy_path | str | クリップボードコピー用パス（SMB: `\\host\path\`、FTP: `ftp://host/path/`） |
| new_files | str[] | 新規検出ファイル名リスト |
| updated_files | str[] | 更新検出ファイル名リスト |

### 4.7 ConnectionTestResponse

| フィールド | 型 | 説明 |
|-----------|-----|------|
| status | str | 結果（`ok` / `error`） |
| file_count | int | 全パス合計検出ファイル数 |
| message | str | サマリメッセージ |
| path_results | PathTestResult[] | パスごとの結果 |

### 4.8 ScanResultResponse

| フィールド | 型 | 説明 |
|-----------|-----|------|
| file_count | int | スキャン対象ファイル総数 |
| new_count | int | 新規ファイル数 |
| updated_count | int | 更新ファイル数 |
| alerts_created | int | 生成したアラート数（0 または 1） |
| message | str | サマリメッセージ |
| changed_paths | ChangedPathInfo[] | 変更が検出されたパスの詳細 |
| content_read_files | int | コンテンツ読み込みを行ったファイル数（full_import 時） |

---

## 5. スキャン処理詳細

### 5.1 スキャンフロー

```
scan_source(db, source_id)
    ↓
1. ソース存在確認・認証情報復号
    ↓
2. 有効パスリスト取得（is_enabled=True のみ）
    ↓
3. RemoteConnector 作成・接続
    ↓
4. for each enabled_path:
       connector.list_files(base_path, file_pattern, modified_since=today)
       ↓
       for each remote_file:
           既存 log_file と比較（サイズ・更新日時）
           → new / updated / unchanged を判定
           → crud_log_file.upsert_file() でDB更新
       ↓
       当日リストに含まれないファイル → status="deleted"
    ↓
5. [alert_on_change AND 変更あり] コンテンツ読み取りフェーズ（full_import のみ）
       connector.read_lines() → log_entries にバルク登録
       last_read_line 更新（差分取込用）
    ↓
6. commit
    ↓
7. [alert_on_change AND 変更あり] アラート生成 + WebSocket ブロードキャスト
    ↓
8. ScanResultResponse を返却
```

### 5.2 今日のファイルのみスキャン

スキャン対象は **`file_modified_at.date() == today`** のファイルのみ。
`connector.list_files()` に `modified_since=today` を渡し、コネクター側でも早期フィルタ可能。
これにより過去ファイルの再スキャンを防ぎ、処理を軽量化する。

### 5.3 ファイル変更検出

| 判定条件 | status | 説明 |
|---------|--------|------|
| DB に存在しない | `new` | 新規検出 |
| `file_size` または `file_modified_at` が変化 | `updated` | タイムスタンプ・サイズ変更 |
| サイズ・更新日時ともに一致 | `unchanged` | 変更なし |
| 当日リストにない（前回はあった） | `deleted` | リモートから削除/移動 |

### 5.4 パスタイムアウト

各パスのスキャンは `LOG_SCAN_PATH_TIMEOUT`（デフォルト 300 秒）でタイムアウトする。
UNIX のみ（SIGALRM 使用）。タイムアウト時はそのパスをスキップし、残りパスを継続。

### 5.5 エラーハンドリング

| エラー種別 | 動作 |
|-----------|------|
| 接続失敗（全体） | DB コミットせず `update_scan_state(error=...)` → エラーレスポンス返却 |
| パス単位のエラー | そのパスをスキップ、残りパス継続、`path_errors` に記録 |
| パスタイムアウト | `ScanTimeoutError` → そのパスをスキップして継続 |
| コンテンツ読み取り失敗 | そのファイルのみスキップ（警告ログ） |
| 認証情報復号失敗 | 即時エラーレスポンス |

パスエラーがある場合、`message` に `"N path error(s)"` が付加される。

### 5.6 content_read_files（full_import + alert_on_change）

`alert_on_change=True` かつ変更ファイルがある場合のみ、変更ファイルのコンテンツを読む:

1. `read_lines(offset=last_read_line, limit=LOG_ALERT_CONTENT_MAX_LINES)` で新規行を取得
2. `parser_pattern` で各行をパース（severity / message 抽出）
3. `log_entries` にバルク登録
4. `last_read_line` を更新
5. 読み取ったエントリの最後 50 行をアラートメッセージに付加

---

## 6. アラート連携

### 6.1 has_alert 判定

```python
has_alert = source.alert_on_change AND source.is_enabled AND (new_count > 0 OR updated_count > 0)
```

この条件が満たされた場合:
- `GET /api/log-sources/status` のレスポンスで `has_alert=true`・`changed_paths` に詳細を含める
- スキャン時にアラートが自動生成される

### 6.2 生成されるアラートの内容

| フィールド | 値 |
|-----------|-----|
| title | `[{source.name}] File changes detected` |
| message | ソース名・変更ファイル数・パスごとのファイル名リスト（+ コンテンツ最後50行） |
| severity | `warning` |
| source | `log_source:{source.id}` |
| rule_id | null（ルールなし、スキャン起動のアラート） |

### 6.3 WebSocket ブロードキャスト

アラート生成後、`alert_ws_manager.broadcast({"type": "new_alert", "alert": {...}})` を呼び出す。
これにより Alerts ページのナビバッジがリアルタイム更新される。

---

## 7. フォルダリンク生成

画面からフォルダを開く際に使用するリンクを生成する。

| access_method | folder_link 形式 | copy_path 形式 |
|---------------|----------------|---------------|
| smb | `file://///{host}/{path}/` | `\\{host}\{path}\` |
| ftp | `ftp://{host}:{port}/{path}/` | `ftp://{host}:{port}/{path}/` |

- `folder_link`: ブラウザ/OSによるフォルダ開き用（`file://` は多くのブラウザでブロック）
- `copy_path`: クリップボードにコピーして Explorer のアドレスバーに貼り付ける用

---

## 8. 認証情報暗号化

### 8.1 Fernet 暗号化

`username` / `password` は保存時に Fernet（AES-128-CBC + HMAC-SHA256）で暗号化する。

```python
# 保存時: encrypt_value(plain_text) → 暗号化テキスト
# 取得時: decrypt_value(encrypted_text) → 平文
```

### 8.2 設定

| 環境変数 | 説明 |
|---------|------|
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet キー（`Fernet.generate_key()` の出力形式）。未設定時はソース作成不可 |

### 8.3 ユーザー名マスク

レスポンスの `username_masked` は先頭 1 文字 + `****` の形式（例: `a****`）。

---

## 9. バックグラウンドスキャナー

### 9.1 概要

`app/services/log_scanner.py` が非同期タスクとして動作し、有効な LogSource を自動スキャンする。

### 9.2 設定

| 環境変数 | デフォルト | 説明 |
|---------|----------|------|
| `LOG_SCANNER_ENABLED` | `false` | スキャナーの有効/無効 |
| `LOG_SCANNER_LOOP_INTERVAL` | `30` | メインループの間隔（秒） |
| `LOG_SCAN_PATH_TIMEOUT` | `300` | パス単位のスキャンタイムアウト（秒） |
| `LOG_ALERT_CONTENT_MAX_LINES` | `200` | コンテンツ読み取り最大行数 |

### 9.3 ライフサイクル

```python
# main.py lifespan
async def lifespan(app: FastAPI):
    await start_scanner(app)    # LOG_SCANNER_ENABLED=true の場合のみ起動
    yield
    await stop_scanner(app)     # CancelledError を catch してクリーンシャットダウン
```

- タスクは `app.state.log_scanner_task` に保存
- `stop_scanner()` はタスクをキャンセルし `CancelledError` / `RuntimeError` をキャッチ

### 9.4 スキャンループ

```
while True:
    sources = get_enabled_log_sources(db)
    now = datetime.now(UTC)
    for source in sources:
        if source.last_checked_at is not None:
            elapsed = (now - source.last_checked_at).total_seconds()
            if elapsed < source.polling_interval_sec:
                continue  # まだ間隔が経過していない
        # 別スレッドでスキャン実行（FTP/SMB はブロッキングI/O）
        result = await asyncio.to_thread(_scan_in_thread, source.id)
        if result["alert_broadcast"]:
            await alert_ws_manager.broadcast(...)
    await asyncio.sleep(LOG_SCANNER_LOOP_INTERVAL)
```

- 各 LogSource の `polling_interval_sec` を個別に尊重
- `scan_source()` は同期 I/O のため `asyncio.to_thread()` でスレッドプールで実行
- ソースごとに独立したエラーハンドリング（1 ソースのエラーが他に影響しない）

---

## 10. RemoteConnector

### 10.1 抽象インターフェース

```python
class RemoteConnector(ABC):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def list_files(self, path, pattern, modified_since=None) -> List[RemoteFileInfo]: ...
    def read_lines(self, path, file_name, offset=0, limit=None, encoding="utf-8") -> List[str]: ...

    # コンテキストマネージャー対応
    def __enter__(self): self.connect(); return self
    def __exit__(self, ...): self.disconnect()
```

### 10.2 RemoteFileInfo

| フィールド | 型 | 説明 |
|-----------|-----|------|
| name | str | ファイル名 |
| size | int | ファイルサイズ（バイト） |
| modified_at | datetime\|null | 更新日時（タイムゾーン付き） |

### 10.3 接続設定

| 設定 | FTP デフォルト | SMB デフォルト |
|------|--------------|--------------|
| port | 21 | 445 |
| connect timeout | `LOG_FTP_CONNECT_TIMEOUT`（30秒） | - |
| read timeout | `LOG_FTP_READ_TIMEOUT`（60秒） | - |

---

## 11. ビジネスルール

### 11.1 認可

| 操作 | 必要権限 | 理由 |
|------|---------|------|
| ソース一覧・詳細・ステータス・ファイル一覧 | 認証ユーザー | チーム全体で参照可能 |
| ソース作成・更新・削除 | **Admin のみ** | 接続情報（パスワード等）を扱うため |
| 接続テスト・スキャン・再読込 | **Admin のみ** | リモートサーバーアクセスを伴うため |

### 11.2 パスバリデーション

| ルール | 説明 |
|--------|------|
| `paths` は 1 件以上必須 | 作成・更新ともに空リストは `422` |
| `access_method` | `ftp` または `smb` のみ |
| `polling_interval_sec` | 60〜3600 の範囲（設定変数 `LOG_SOURCE_MIN/MAX_POLLING_SEC` で変更可） |
| `parser_pattern` | 有効な Python 正規表現であること |
| `collection_mode` | `metadata_only` または `full_import` のみ |
| `source_type` | `WEB` / `HT` / `BATCH` / `OTHER` のいずれか |

### 11.3 暗号化必須

`CREDENTIAL_ENCRYPTION_KEY` が未設定の場合、`create_source()` は `400 ConflictError` を返す。
本番運用前に必ず設定が必要。

### 11.4 スキャン対象

スキャンは **当日（`modified_since=today`）のファイルのみ**を対象とする。
これにより、過去の大量ファイルを毎回スキャンする無駄を防ぐ。

---

## 12. フロントエンド

### 12.1 画面構成（`/logs` ページの下部セクション）

Log Sources セクションはログ画面（`/logs`）の下部に統合されている。

```
/logs ページ
├── System Logs セクション（上部）
│   └── WebSocket リアルタイムログ表示
└── Log Sources セクション（下部）
    ├── ソースステータステーブル
    └── 編集モーダル（Add/Edit Source）
```

### 12.2 ソースステータステーブル

`GET /api/log-sources/status` でデータ取得。

| 列 | 内容 |
|----|------|
| Name | ソース名 |
| Group | グループ名 |
| Host | ホスト名/IP |
| Type | source_type |
| Mode | collection_mode |
| Paths | 監視パス数 |
| Status | 有効/無効バッジ + エラーバッジ + アラートドット（赤） |
| Last Checked | last_checked_at（"Never" if null） |
| Error | last_error（折り畳み表示） |
| Changed Files | has_alert=true 時にフォルダリンク・ファイル名を表示 |
| Actions | Test / Scan / Edit / Delete |

**has_alert 表示**: 赤いドット（●）と `changed_paths` 内の変更ファイル名リスト、フォルダリンクボタンを表示。

### 12.3 編集モーダル（タブ構成）

| タブ | 内容 |
|------|------|
| Basic | Name / Group / Access Method / Host / Port / Username / Password / Domain |
| Paths | パスリスト（追加・削除・有効化） |
| Settings | Encoding / Source Type / Polling Interval / Collection Mode |
| Parser | Parser Pattern / Severity Field / Default Severity |
| Options | Alert on Change / Is Enabled |

### 12.4 主要 JS 関数

| 関数 | 説明 |
|------|------|
| `loadSourceStatuses()` | `GET /api/log-sources/status` で取得・描画 |
| `openAddSourceModal()` | 新規作成モーダル初期化 |
| `openEditSourceModal(id)` | `GET /api/log-sources/{id}` で取得 → モーダル表示 |
| `saveSource()` | 新規: POST / 編集: PUT |
| `testConnection(id)` | 接続テスト実行 + 結果表示 |
| `scanSource(id)` | スキャン実行 + 結果表示 |
| `deleteSource(id)` | confirm 後に DELETE |
| `renderChangedPaths(changedPaths)` | フォルダリンク・ファイル名表示 |
| `copyToClipboard(text)` | copy_path をクリップボードにコピー |

---

## 13. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/log_source.py` | `LogSource` ORM モデル |
| `app/models/log_source_path.py` | `LogSourcePath` ORM モデル |
| `app/models/log_file.py` | `LogFile` ORM モデル |
| `app/models/log_entry.py` | `LogEntry` ORM モデル |
| `app/schemas/log_source.py` | スキーマ定義（Create/Update/Response/Status/Scan/Test） |
| `app/schemas/log_file.py` | `LogFileResponse` スキーマ |
| `app/schemas/log_entry.py` | `LogEntryResponse` スキーマ |
| `app/crud/log_source.py` | LogSource CRUD（暗号化認証情報の保存は Service 層） |
| `app/crud/log_source_path.py` | LogSourcePath CRUD |
| `app/crud/log_file.py` | LogFile CRUD（upsert/mark_deleted/count/get_changed） |
| `app/crud/log_entry.py` | LogEntry CRUD（bulk_insert/delete_by_source/reset） |
| `app/services/log_source_service.py` | ビジネスロジック（CRUD + scan + re-read + connection test） |
| `app/services/log_scanner.py` | バックグラウンドスキャナー（asyncio タスク） |
| `app/services/remote_connector.py` | FTP/SMB 接続抽象インターフェース + 実装 |
| `app/core/encryption.py` | `encrypt_value` / `decrypt_value` / `mask_username` (Fernet) |
| `app/routers/api_log_sources.py` | REST API ルーター（10 エンドポイント） |
| `app/config.py` | `LOG_SCANNER_ENABLED`, `LOG_SCAN_PATH_TIMEOUT`, `CREDENTIAL_ENCRYPTION_KEY` 等 |
| `main.py` | lifespan で `start_scanner` / `stop_scanner` |
| `templates/logs.html` | Log Sources セクション（テーブル + モーダル） |
| `static/js/logs.js` | Log Sources JS |
| `tests/test_log_sources.py` | LogSource API テスト（100 件） |
| `tests/test_log_scanner.py` | バックグラウンドスキャナーテスト（11 件） |

---

## 14. テスト

### 14.1 test_log_sources.py（100 件）

| グループ | 件数 | 内容 |
|---------|------|------|
| 基本 CRUD | 50 | 作成・取得・更新・削除、暗号化確認、username マスク、group_id 検証 |
| 複数パス（Multi-Path） | 13 | パス追加・更新・削除の reconcile、パス有効化 |
| スキャン・アラート連携 | 16 | 新規/更新/削除ファイル検出、alert_on_change フラグ、has_alert 計算 |
| 接続テスト | 7 | 成功/失敗/部分成功、last_checked_at 更新 |
| バリデーション | 8 | access_method 不正・collection_mode 不正・regex 不正・polling_interval 範囲外・paths 空 |
| RBAC | 6 | 非 Admin の CUD 操作は 403 |

### 14.2 test_log_scanner.py（11 件）

| テスト | 検証内容 |
|--------|---------|
| `test_scanner_start_stop` | `LOG_SCANNER_ENABLED=true` 時のタスク起動・停止 |
| `test_scanner_disabled` | `LOG_SCANNER_ENABLED=false` 時はタスク未起動 |
| `test_scan_due_source` | `polling_interval_sec` が経過したソースのみスキャン |
| `test_skip_not_due_source` | 間隔未経過のソースはスキップ |
| `test_alert_broadcast_on_scan` | スキャンでアラートが生成された場合に WebSocket ブロードキャスト |
| `test_error_isolation` | 1 ソースのエラーが他のソースのスキャンをブロックしない |
| 他 5 件 | セッション管理・エラーハンドリング・スキャン後のステータス更新 |

---

## 15. マイグレーション

| リビジョン | 説明 |
|-----------|------|
| `3c7419e092cb` | log_sources v2 再設計（FTP/SMB リモート接続、暗号化認証情報） |
| `b8f2a1c3d4e5` | log_source_paths テーブル追加、log_files に path_id 追加 |
| `0d0894c74444` | log_sources に alert_on_change カラム追加 |
| `c1a2b3d4e5f6` | log_sources の server_name を削除し group_id (FK groups.id) に置換 |

---

## 16. 技術的負債・既知の制限

| 項目 | 内容 |
|------|------|
| FTP パッシブモード限定 | 現行 FTP コネクターはパッシブモードのみ対応。アクティブモード未対応 |
| SIGALRM によるタイムアウト | Unix/Linux のメインスレッドでのみ動作。Windows・非メインスレッドでは no-op |
| コンテンツ読み取り上限 | `LOG_ALERT_CONTENT_MAX_LINES`（デフォルト 200 行）でファイルコンテンツの取り込み量を制限。大きなログファイルは末尾 200 行のみ |
| 暗号化キー更新 | `CREDENTIAL_ENCRYPTION_KEY` ローテーション時、既存の暗号化データを再暗号化する手順が未整備 |
| 詳細は `docs/spec_log_problem.md` 参照 | - |
