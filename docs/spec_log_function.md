# ログファイル収集機能 設計書 (v2)

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。
> 質問事項は [spec_log_function_qa2.md](./spec_log_function_qa2.md) を参照してください。
> 初版 Q&A の回答: [spec_log_function_qa.md](./spec_log_function_qa.md)

---

## 1. 概要

### 1.1 背景と目的

リモートサーバ上のログファイルを一元管理し、Web UI から効率的に閲覧・監視できるログ収集システムを提供する。膨大なログを全件 DB に保存するのではなく、**メタデータ管理（ファイル一覧・タイムスタンプ）+ 重要ログの DB 全件取込み**の二段構えの設計とする。metadata_only モードではファイルのメタデータのみを管理し、ログ内容の閲覧はユーザーがサーバに直接アクセスして行う。full_import モードでは DB に保存されたログを Web UI から閲覧できる。

### 1.2 設計方針

| 方針 | 内容 |
|------|------|
| ストレージ最小化 | ログ本文の DB 保存は必要最小限（full_import モードのみ） |
| メタデータ管理 | metadata_only モードではファイルのメタデータ（名前・サイズ・更新日時）のみ管理。Web UI でのログ内容閲覧は不可。ユーザーがサーバに直接アクセスして確認する |
| リモートアクセス | FTP / Windows ファイル共有 (SMB) でサーバからログを取得 |
| 閲覧性重視 | ソース単位のダッシュボード + ファイルツリー型の UI |
| アラート連携 | full_import モードのログのみアラートルール評価対象 |
| 自動クリーンアップ | 90 日（設定可能）経過した DB ログを自動削除 |

### 1.3 機能一覧

| 機能 | 説明 |
|------|------|
| ログソース管理 | リモートサーバの接続情報・収集設定の登録・編集・削除（admin） |
| ファイルスキャン | リモートフォルダをポーリングし、ファイルのメタデータ（名前・サイズ・更新日時）を DB に記録 |
| メタデータ閲覧 | ソース一覧 → ファイル一覧の階層的ナビゲーション。metadata_only モードではファイル名・サイズ・更新日時のみ表示（ログ内容の Web 閲覧は不可、ユーザーがサーバに直接アクセスして確認） |
| 全件取込 | full_import モードの対象ファイルを行単位で DB に保存（増分読取） |
| アラート連携 | full_import で取込んだログに対してアラートルール評価・自動生成 |
| 自動削除 | 保持期間を超えた log_entries を定期的に物理削除 |
| 認証情報管理 | FTP/SMB の接続認証情報を暗号化して DB に保存 |

---

## 2. アーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    ログ収集サブシステム                           │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────────────┐             │
│  │ ログソース    │     │ バックグラウンドスキャナー │             │
│  │ 管理 API     │     │ (_scanner_loop)           │             │
│  │ (admin)      │     │                           │             │
│  └──────┬───────┘     │ ┌─────────────────────┐  │             │
│         │             │ │ リモート接続          │  │             │
│         ▼             │ │ FTP / SMB            │──┼──▶ リモートサーバ
│  ┌──────────────┐     │ └─────────┬───────────┘  │             │
│  │ log_sources  │◀────┤           │              │             │
│  │ テーブル     │     │           ▼              │             │
│  └──────────────┘     │ ┌─────────────────────┐  │             │
│                       │ │ ファイルメタデータ    │  │             │
│  ┌──────────────┐     │ │ 収集 + 差分検出      │  │             │
│  │ log_files    │◀────┤ └─────────┬───────────┘  │             │
│  │ テーブル     │     │           │              │             │
│  └──────┬───────┘     │           ▼              │             │
│         │             │ ┌─────────────────────┐  │             │
│  ┌──────▼───────┐     │ │ full_import:         │  │             │
│  │ log_entries  │◀────┤ │ 行読取 + DB 保存     │  │             │
│  │ テーブル     │     │ │ + アラート評価       │  │             │
│  └──────────────┘     │ └─────────────────────┘  │             │
│                       └──────────────────────────┘             │
│                                                                 │
│  ┌──────────────────────────────────────┐                      │
│  │ コンテンツ取得 API                    │                      │
│  │ GET /api/log-sources/{id}/files/     │                      │
│  │     {file_id}/content                │                      │
│  │ (full_import 時のみ: DB から取得)     │                      │
│  │ ※ metadata_only は Web 閲覧不可      │                      │
│  └──────────────────────────────────────┘                      │
│                                                                 │
│  ┌──────────────────┐                                          │
│  │ 自動クリーンアップ │                                          │
│  │ (90日超ログ削除)  │                                          │
│  └──────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 収集モード比較

| 項目 | metadata_only | full_import |
|------|--------------|-------------|
| ファイルスキャン | ファイル名・サイズ・更新日時を DB に記録 | 同左 |
| ログ本文の DB 保存 | しない | 全行を log_entries に保存 |
| ログ閲覧方法 | Web UI では閲覧不可（ファイルメタデータのみ表示）。ユーザーがサーバに直接アクセスして確認 | DB から取得（Web UI で閲覧可能） |
| 増分読取 | なし | 行番号ベースで増分読取 |
| アラート評価 | なし | 取込時にルール評価 |
| 用途 | 通常ログ（アクセスログ等） | 重要ログ（エラーログ等） |
| DB 容量 | 最小（メタデータのみ） | ログ量に比例 |

### 2.3 レイヤー構成

```
[ルーター層]
  api_log_sources.py   — ログソース管理 + ファイル一覧 + スキャン
      ↓
[サービス層]
  log_source_service.py  — ログソース CRUD + 手動スキャン（scan_source）
  remote_connector.py    — FTP/SMB 接続抽象化（実装済み）
  alert_service.py       — アラートルール評価（連携先、既存）
  log_scanner.py         — バックグラウンドスキャナー（実装済み）
  log_importer.py        — full_import モードのログ取込（未実装）
  log_cleanup.py         — 自動クリーンアップ（未実装）
      ↓
[CRUD層]
  log_source.py          — log_sources テーブル操作
  log_source_path.py     — log_source_paths テーブル操作
  log_file.py            — log_files テーブル操作
  log_entry.py           — log_entries テーブル操作
      ↓
[モデル層]
  log_source.py          — LogSource ORM モデル（リモート接続情報含む）
  log_source_path.py     — LogSourcePath ORM モデル（監視パス）
  log_file.py            — LogFile ORM モデル
  log_entry.py           — LogEntry ORM モデル
```

---

## 3. データモデル

### 3.1 ER 図

```
log_sources (1) ──── (N) log_files (1) ──── (N) log_entries

alert_rules (既存) ── アラート評価 ── log_entries (full_import)
```

### 3.2 log_sources テーブル（LOG 管理テーブル）

リモートサーバの接続情報と収集設定を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ログソース ID |
| name | String(200) | NOT NULL | 表示名 |
| group_id | Integer | FK(groups.id), NOT NULL | グループID |
| access_method | String(10) | NOT NULL | アクセス方法 (`ftp` / `smb`) |
| host | String(255) | NOT NULL | ホスト名 / IP アドレス |
| port | Integer | NULL 許可 | ポート番号（NULL=デフォルト: FTP=21, SMB=445） |
| username | String(500) | NOT NULL | 接続ユーザー名（暗号化） |
| password | String(500) | NOT NULL | 接続パスワード（暗号化） |
| base_path | String(1000) | NOT NULL | リモートフォルダパス |
| file_pattern | String(200) | NOT NULL, DEFAULT "\*" | ファイル名パターン（glob 形式: `*.log`, `error*.txt`） |
| encoding | String(20) | NOT NULL, DEFAULT "utf-8" | ファイルエンコーディング |
| polling_interval_sec | Integer | NOT NULL, DEFAULT 60 | ポーリング間隔（秒、60〜3600） |
| collection_mode | String(20) | NOT NULL, DEFAULT "metadata_only" | 収集モード |
| parser_pattern | Text | NULL 許可 | 正規表現パーサー（full_import 時のみ使用） |
| severity_field | String(100) | NULL 許可 | severity 抽出グループ名 |
| default_severity | String(20) | NOT NULL, DEFAULT "INFO" | デフォルト severity |
| is_enabled | Boolean | NOT NULL, DEFAULT true | 有効/無効 |
| last_checked_at | DateTime(TZ) | NULL 許可 | 最終スキャン日時 |
| last_error | Text | NULL 許可 | 最終エラー（成功時 NULL クリア） |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/log_source.py`
- `username` / `password` は Fernet 暗号化して保存（`CREDENTIAL_ENCRYPTION_KEY` 環境変数）

**access_method 値:**

| 値 | プロトコル | デフォルトポート | ライブラリ |
|----|----------|----------------|-----------|
| `ftp` | FTP | 21 | `ftplib` (標準ライブラリ) |
| `smb` | SMB/CIFS (Windows 共有) | 445 | `smbprotocol` |

**collection_mode 値:**

| 値 | 説明 |
|----|------|
| `metadata_only` | ファイルメタデータのみ記録（Web UI でのログ内容閲覧は不可） |
| `full_import` | ファイル内容を全行 DB に取込み（アラート評価対象） |

### 3.3 log_files テーブル（LOG ヘッダテーブル）

検出されたログファイルのメタデータを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ファイル ID |
| source_id | Integer | FK(log_sources.id, CASCADE), NOT NULL, INDEX | ログソース ID |
| file_name | String(500) | NOT NULL | ファイル名 |
| file_size | BigInteger | NOT NULL, DEFAULT 0 | ファイルサイズ（バイト） |
| file_modified_at | DateTime(TZ) | NULL 許可 | ファイル最終更新日時（リモート側） |
| last_read_line | Integer | NOT NULL, DEFAULT 0 | 最終読取行番号（full_import 用） |
| status | String(20) | NOT NULL, DEFAULT "new" | ファイル状態 |
| created_at | DateTime(TZ) | DEFAULT now() | 初回検出日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 最終更新日時 |

- モデルファイル: `app/models/log_file.py`
- UNIQUE 制約: `(source_id, file_name)`

**status 値:**

| 値 | 説明 |
|----|------|
| `new` | 新規検出（未読取） |
| `unchanged` | 前回スキャンから変更なし |
| `updated` | 前回スキャンからサイズまたはタイムスタンプが変更 |
| `deleted` | リモート側で削除されたファイル |
| `error` | 読取エラー |

### 3.4 log_entries テーブル（LOG 明細テーブル）

full_import モードで取込んだログ行を格納する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | エントリ ID |
| file_id | Integer | FK(log_files.id, CASCADE), NOT NULL, INDEX | ファイル ID |
| line_number | Integer | NOT NULL | ファイル内の行番号 |
| severity | String(20) | NOT NULL, DEFAULT "INFO" | 重要度 |
| message | Text | NOT NULL | ログメッセージ |
| received_at | DateTime(TZ) | DEFAULT now() | 取込日時 |

- モデルファイル: `app/models/log_entry.py`
- 複合インデックス: `(file_id, line_number)`
- 自動削除対象: `received_at` が保持期間（デフォルト 90 日）を超えたレコード

### 3.5 既存テーブルとの関係

| テーブル | 状態 | 説明 |
|---------|------|------|
| `logs` (既存) | **維持** | 将来の API Push パターン用に残す。現行の POST /api/logs/ で使用 |
| `log_sources` (既存) | **置換** | 新 log_sources テーブルに再設計。マイグレーションで移行 |
| `log_files` | **新規** | ファイルメタデータ管理 |
| `log_entries` | **新規** | full_import のログ行格納 |

---

## 4. リモート接続

### 4.1 接続抽象化

`remote_connector.py` で FTP/SMB の差異を吸収するインターフェースを提供する。

```python
class RemoteConnector(ABC):
    """リモートファイルアクセスの抽象インターフェース"""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def list_files(self, path: str, pattern: str) -> List[RemoteFileInfo]: ...

    @abstractmethod
    def read_file(self, path: str, offset: int = 0,
                  limit: Optional[int] = None, encoding: str = "utf-8") -> List[str]: ...

class RemoteFileInfo:
    """リモートファイルのメタデータ"""
    name: str
    size: int
    modified_at: datetime
```

### 4.2 FTP 接続 (`FTPConnector`)

| 項目 | 値 |
|------|-----|
| ライブラリ | `ftplib`（Python 標準ライブラリ） |
| 認証 | ユーザー名 + パスワード |
| ファイル一覧 | `MLSD` コマンド（対応サーバ）または `LIST` フォールバック |
| ファイル読取 | `RETR` コマンドでバイナリ取得 → エンコーディング変換 |
| タイムスタンプ | `MDTM` コマンドまたは `MLSD` の modify フィールド |

### 4.3 SMB 接続 (`SMBConnector`)

| 項目 | 値 |
|------|-----|
| ライブラリ | `smbprotocol`（pip install 必要） |
| 認証 | ユーザー名 + パスワード（NTLM） |
| ファイル一覧 | `smbclient.scandir()` |
| ファイル読取 | `smbclient.open_file()` |
| タイムスタンプ | `DirEntry.stat().st_mtime` |
| 接続プール | `smbprotocol` 内蔵のコネクションキャッシュ |

### 4.4 認証情報の暗号化

| 項目 | 値 |
|------|-----|
| 暗号化方式 | Fernet (AES-128-CBC + HMAC-SHA256) |
| ライブラリ | `cryptography` |
| 鍵管理 | `CREDENTIAL_ENCRYPTION_KEY` 環境変数（`.env` ファイル） |
| 鍵生成 | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| 暗号化対象 | `log_sources.username`, `log_sources.password` |
| API レスポンス | パスワードは返却しない、ユーザー名はマスク表示 |

---

## 5. バックグラウンドスキャナー

> **実装状況**: バックグラウンドスキャナー（`app/services/log_scanner.py`）は**実装済み**。
> `LOG_SCANNER_ENABLED=true` で有効化。`LOG_SCANNER_LOOP_INTERVAL`（デフォルト30秒）ごとにメインループが実行され、各ソースの `polling_interval_sec` 経過分のみスキャンする。
> FTP/SMB の同期I/O は `asyncio.to_thread()` でスレッドプール実行（イベントループをブロックしない）。
> 手動スキャン（`POST /api/log-sources/{id}/scan`）も引き続き利用可能。

### 5.1 概要

`log_scanner.py` に実装されるバックグラウンドタスクで、有効なログソースのリモートフォルダを定期的にスキャンし、ファイルメタデータを更新する。

### 5.2 スキャンフロー

```
_scanner_loop() [無限ループ、SCANNER_LOOP_INTERVAL 秒間隔]
  │
  ├── DB セッション生成
  ├── 有効な log_sources を全件取得
  │
  └── 各 source について:
       │
       ├── polling_interval_sec 経過チェック（未経過ならスキップ）
       │
       ├── [1] リモート接続
       │   └── FTPConnector or SMBConnector を生成・接続
       │
       ├── [2] ファイル一覧取得
       │   └── list_files(base_path, file_pattern)
       │   └── RemoteFileInfo[] を取得
       │
       ├── [3] メタデータ差分更新
       │   ├── 新規ファイル → log_files INSERT (status=new)
       │   ├── 既存ファイル:
       │   │   ├── サイズ or タイムスタンプ変更 → UPDATE (status=updated)
       │   │   └── 変更なし → UPDATE (status=unchanged)
       │   └── リモートに存在しないファイル → UPDATE (status=deleted)
       │
       ├── [4] full_import モードの場合:
       │   ├── status=new or updated のファイルについて:
       │   │   ├── read_file(path, offset=last_read_line)
       │   │   ├── 各行を parse → log_entries INSERT
       │   │   ├── アラートルール評価（非同期キュー）
       │   │   └── last_read_line 更新
       │   └── WebSocket /ws/logs にブロードキャスト
       │
       ├── [5] source.last_checked_at 更新、last_error クリア
       │
       └── エラー時: last_error にメッセージ記録、ループ継続
```

### 5.3 増分読取（full_import モード）

```
ファイル: error.log (100行)
  │
  1回目スキャン:
  │ last_read_line = 0
  │ → 1〜100行目を読取
  │ → log_entries に 100行 INSERT
  │ → last_read_line = 100
  │
  2回目スキャン（status=updated、ファイルが120行に増加）:
  │ last_read_line = 100
  │ → 101〜120行目を読取（増分のみ）
  │ → log_entries に 20行 INSERT
  │ → last_read_line = 120
  │
  ファイルローテーション検出（サイズ縮小）:
  │ → last_read_line = 0 にリセット
  │ → 先頭から再読取
```

### 5.4 ファイル読取の改行対応

- `\n`（Unix）と `\r\n`（Windows）の両方を行区切りとして処理
- ファイルを `encoding` パラメータ指定のエンコーディングで読取（デフォルト UTF-8）
- デコードエラー時は `errors="replace"` で代替文字に置換

---

## 6. アラート連携（非同期評価）

### 6.1 設計変更

**現行**: ログ作成時に同期的にアラートルール全件を評価
**変更後**: バックグラウンドキューで非同期評価（ルール数 100 件を想定）

### 6.2 非同期評価フロー

```
log_importer.py (full_import)
  │
  ├── log_entries に INSERT
  │
  └── alert_queue.enqueue(log_entry_data)
       │
       └── [バックグラウンド]
            ├── 有効ルールを全件取得
            ├── 条件マッチング（$in, $contains, exact）
            └── 一致時: アラート生成 + WebSocket /ws/alerts
```

### 6.3 対象

- **full_import** モードで取込まれた log_entries のみがアラート評価対象
- **metadata_only** モードはアラート評価しない（DB にログ本文がないため）
- 既存の `POST /api/logs/` 経由のログは引き続き同期評価（将来実装時）

---

## 6b. ファイル変更通知（alert_on_change）

### 6b.1 目的

リモートサーバー上のエラーログファイル等を監視し、**ファイルのタイムスタンプが更新されたら画面に「エラーあり」を表示**する。変更があったファイルのフォルダへのリンクを表示し、クリックでフォルダに遷移してログを直接確認できるようにする。

### 6b.2 動作仕様

#### トリガー条件

`alert_on_change=true` のログソースに対してスキャンを実行した際、**ファイル単位**で以下を検出:

| 検出種別 | 条件 | 表示 |
|---------|------|------|
| 新規ファイル | フィルタパターンに一致するファイルが新たに検出された | `NEW` バッジ |
| タイムスタンプ更新 | 既存ファイルの `file_modified_at` または `file_size` が前回と異なる | `UPD` バッジ |

- **当日フィルタ**: `file_modified_at` が今日のファイルのみが対象
- **ファイル単位**: フォルダ内の各ファイルを個別に判定（フォルダ単位ではない）

#### フォルダリンク生成

変更が検出されたパスに対して、接続方式に応じたフォルダリンクを生成:

| access_method | リンク形式 | 動作 |
|---------------|-----------|------|
| `smb` | `file://///host/base_path/` | Windows Explorer でフォルダを直接開く |
| `ftp` | `ftp://host:port/base_path/` | FTP パス表示（コピーして FTP クライアントで接続） |

#### 画面表示

1. **ソースダッシュボード（Logs画面）**:
   - ステータスドット: 赤（ファイル変更検出時）
   - ソース行の下にサブ行を表示:
     - フォルダリンク（クリックでサーバー上のフォルダに遷移）
     - 変更ファイル名の一覧（NEW/UPD バッジ付き）
   - ユーザーはフォルダリンクをクリック → Explorer 等でフォルダを開く → ログファイルを確認

2. **アラート（Alerts画面 + WebSocket通知）**:
   - タイトル: `[ソース名] ファイル変更検出`
   - メッセージ: 変更ファイル名 + フォルダパスを含む
   - severity: `warning`

### 6b.3 データフロー

```
スキャン実行（手動 or バックグラウンド）
  │
  ├── リモート接続 → ファイル一覧取得
  │
  ├── 当日フィルタ（file_modified_at.date() == today）
  │
  ├── 各ファイルのタイムスタンプ/サイズ比較
  │   ├── 変更あり → status=new/updated, changed_paths に追加
  │   └── 変更なし → status=unchanged
  │
  ├── DB 更新（upsert_file）
  │
  ├── alert_on_change=true AND 変更ファイルあり:
  │   ├── コンテンツ読み込み（差分読取）
  │   │   ├── 各変更ファイルの last_read_line 以降を読取（最大 LOG_ALERT_CONTENT_MAX_LINES 行）
  │   │   ├── parser_pattern で severity 抽出
  │   │   ├── log_entries にバルクインサート
  │   │   └── last_read_line 更新
  │   ├── アラート生成（変更ファイル名 + フォルダパス + ログ内容含む）
  │   └── WebSocket /ws/alerts にブロードキャスト
  │
  └── レスポンス（ScanResultResponse + changed_paths + content_read_files）
```

### 6b.4 API レスポンス

スキャン結果（`ScanResultResponse`）と ステータス一覧（`LogSourceStatusResponse`）の両方に `changed_paths` を含める:

```json
{
  "changed_paths": [
    {
      "path_id": 3,
      "base_path": "logs/errors",
      "folder_link": "file://///192.168.1.10/logs/errors/",
      "new_files": ["app_error_20260218.log"],
      "updated_files": ["system.err", "batch.err"]
    }
  ]
}
```

---

## 7. 自動クリーンアップ

### 7.1 仕様

| 項目 | 値 |
|------|-----|
| 対象テーブル | `log_entries` |
| 保持期間 | デフォルト 90 日（`LOG_RETENTION_DAYS` 環境変数で設定可能） |
| 削除方式 | 物理削除 |
| 実行タイミング | スキャナーループ内で定期実行（1 日 1 回） |
| 権限 | 自動実行（admin 操作不要） |
| 削除条件 | `received_at < now() - LOG_RETENTION_DAYS` |

### 7.2 関連テーブルの整合性

- `log_entries` 削除後、`log_files.last_read_line` はリセットしない（ファイル側は増分読取を継続）
- `status=deleted` かつ `log_entries` が 0 件の `log_files` レコードは削除候補（要検討: Q&A2 参照）

---

## 8. API エンドポイント

### 8.1 ログソース管理 API (`/api/log-sources`)

| メソッド | パス | 説明 | 認証 | ステータス |
|---------|------|------|------|-----------|
| GET | `/api/log-sources/` | ソース一覧 | 必要 | 200 |
| POST | `/api/log-sources/` | ソース作成 | admin | 201 |
| GET | `/api/log-sources/{id}` | ソース詳細 | 必要 | 200/404 |
| PUT | `/api/log-sources/{id}` | ソース更新 | admin | 200/404 |
| DELETE | `/api/log-sources/{id}` | ソース削除 | admin | 204/404 |
| POST | `/api/log-sources/{id}/test` | 接続テスト | admin | 200/400 |

#### POST /api/log-sources/{id}/test（新規）

リモートサーバへの接続テスト。ファイル一覧の取得を試行し、結果を返却する。

- **レスポンス (成功)**: `200 OK`
  ```json
  {
    "status": "ok",
    "file_count": 15,
    "message": "Connected successfully. Found 15 files matching pattern."
  }
  ```
- **レスポンス (失敗)**: `400 Bad Request`
  ```json
  {
    "status": "error",
    "message": "Connection refused: 192.168.1.100:21"
  }
  ```

### 8.2 ファイル一覧・コンテンツ API

| メソッド | パス | 説明 | 認証 | ステータス |
|---------|------|------|------|-----------|
| GET | `/api/log-sources/{id}/files` | ファイル一覧 | 必要 | 200/404 |
| GET | `/api/log-sources/{id}/files/{file_id}/content` | ファイル内容取得 | 必要 | 200/404 |

#### GET /api/log-sources/{id}/files

ソースに紐づくファイル一覧を取得する。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| status | string | null | ステータスフィルタ（new/updated/unchanged/deleted） |
| sort | string | "modified_desc" | ソート順（modified_desc/modified_asc/name_asc/name_desc） |

- **レスポンス**: `200 OK` - `LogFileResponse[]`

#### GET /api/log-sources/{id}/files/{file_id}/content

ファイルの内容を取得する。**full_import モード専用**。

- **full_import モード**: DB の log_entries から取得
- **metadata_only モード**: `400 Bad Request` を返却（Web UI でのログ内容閲覧は不可。ユーザーはサーバに直接アクセスしてファイルを確認する）

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| offset | integer | 0 | 開始行番号 |
| limit | integer | 500 | 取得行数 |

- **レスポンス**: `200 OK`
  ```json
  {
    "file_name": "error.log",
    "total_lines": 1250,
    "offset": 0,
    "limit": 500,
    "lines": [
      {"line_number": 1, "content": "2026-02-18 10:00:00 ERROR Connection timeout"},
      {"line_number": 2, "content": "2026-02-18 10:00:01 INFO Retrying..."}
    ]
  }
  ```

### 8.3 ログ検索 API（新規）

| メソッド | パス | 説明 | 認証 | ステータス |
|---------|------|------|------|-----------|
| GET | `/api/log-entries/search` | ログ検索 | 必要 | 200 |

- **クエリパラメータ**: （検索条件の詳細は要検討: Q&A2 参照）

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| source_id | integer | null | ソース ID フィルタ |
| severity | string | null | severity フィルタ |
| keyword | string | null | メッセージ部分一致 |
| from_date | datetime | null | 取込日時の開始 |
| to_date | datetime | null | 取込日時の終了 |
| limit | integer | 100 | 取得件数 |
| offset | integer | 0 | オフセット |

- **対象**: full_import モードで DB に保存された log_entries のみ

### 8.4 既存 API の維持

| メソッド | パス | 状態 | 説明 |
|---------|------|------|------|
| POST | `/api/logs/` | **維持** | 外部 API Push 用（将来実装時に使用） |
| GET | `/api/logs/` | **維持** | 既存 logs テーブルの一覧取得 |
| GET | `/api/logs/important` | **維持** | 既存 logs テーブルの重要ログ |

---

## 9. 画面設計（UI）

### 9.1 ログ画面のリニューアル (`/logs`)

現行のフラットなログ一覧を、**ソースダッシュボード + ファイルエクスプローラー型**に刷新する。

#### レイアウト構成

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍 ログモニター                               [+ ソース追加]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ 🖥 Web-Server   │ │ 🖥 DB-Server    │ │ 🖥 App-Server   │  │
│  │ FTP 192.168.1.10│ │ SMB \\db-01     │ │ FTP 10.0.0.5    │  │
│  │ /var/log/httpd/ │ │ logs$\sql\      │ │ /opt/app/logs/  │  │
│  │                 │ │                 │ │                 │  │
│  │ 📁 12 files     │ │ 📁 5 files      │ │ 📁 8 files      │  │
│  │ 🆕 3 new        │ │ 🔄 1 updated    │ │ ✅ no changes   │  │
│  │ ⏱ 2分前         │ │ ⏱ 5分前         │ │ ⏱ 1分前         │  │
│  │ ● 接続OK        │ │ ● 接続OK        │ │ ⚠ エラー        │  │
│  │                 │ │                 │ │                 │  │
│  │ [メタデータ]     │ │ [全件取込]       │ │ [メタデータ]     │  │
│  └────────┬────────┘ └────────┬────────┘ └─────────────────┘  │
│           │                   │                                │
│  ─────────▼───────────────────┘                                │
│                                                                 │
│  ─── metadata_only ソースの場合（例: Web-Server）───            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Web-Server — /var/log/httpd/  (12 files) [メタデータ]     │  │
│  ├──────────┬──────────┬──────────────┬────────────────────┤  │
│  │ Status   │ File     │ Modified     │ Size               │  │
│  ├──────────┼──────────┼──────────────┼────────────────────┤  │
│  │ 🆕 NEW   │ error.log│ 02/18 10:30  │ 2.4 MB             │  │
│  │ 🔄 UPD   │ access.. │ 02/18 10:28  │ 15 MB              │  │
│  │ — same   │ ssl_err..│ 02/17 23:00  │ 128 KB             │  │
│  │ ...      │          │              │                    │  │
│  └──────────┴──────────┴──────────────┴────────────────────┘  │
│  ※ metadata_only: View ボタンなし（ログ内容はサーバで直接確認） │
│                                                                 │
│  ─── full_import ソースの場合（例: DB-Server）───               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ DB-Server — logs$\sql\  (5 files) [全件取込]              │  │
│  ├──────────┬──────────┬──────────────┬────────┬───────────┤  │
│  │ Status   │ File     │ Modified     │ Size   │ Actions   │  │
│  ├──────────┼──────────┼──────────────┼────────┼───────────┤  │
│  │ 🆕 NEW   │ error.log│ 02/18 10:30  │ 2.4 MB │ [View]    │  │
│  │ 🔄 UPD   │ sql_err..│ 02/18 10:28  │ 800 KB │ [View]    │  │
│  │ ...      │          │              │        │           │  │
│  └──────────┴──────────┴──────────────┴────────┴───────────┘  │
│                                                                 │
│  ─── [View] クリック時（full_import のみ）───                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ error.log — DB-Server                     [閉じる] [↻]   │  │
│  │ 2,450 lines | 2.4 MB | Last modified: 02/18 10:30       │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ 1  2026-02-18 10:30:01 ERROR Connection refused to db   │  │
│  │ 2  2026-02-18 10:30:02 INFO  Retrying connection...     │  │
│  │ 3  2026-02-18 10:30:05 ERROR Timeout after 3 retries    │  │
│  │ ...                                                      │  │
│  │ [< Prev 500] [Next 500 >]                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### ソースカードの表示要素

| 要素 | 説明 |
|------|------|
| グループ名 | `log_sources.group_id` → `groups.name` |
| 接続情報 | アクセス方法 + ホスト |
| フォルダパス | `log_sources.base_path` |
| ファイル数 | `log_files` のカウント |
| 変更ファイル数 | status=new/updated のカウント（バッジ表示） |
| 最終スキャン | `log_sources.last_checked_at` の経過時間 |
| 接続状態 | `last_error` の有無で ●接続OK / ⚠エラー |
| 収集モード | metadata_only / full_import のラベル |

#### ファイル一覧のステータスバッジ

| status | 表示 | 色 |
|--------|------|-----|
| `new` | 🆕 NEW | 青 (primary) |
| `updated` | 🔄 UPD | 黄 (warning) |
| `unchanged` | — | グレー (secondary) |
| `deleted` | 🗑 DEL | 赤 (danger) |
| `error` | ⚠ ERR | 赤 (danger) |

#### ファイルビューア（full_import モード専用）

- **full_import ソースのみ**: View ボタンでファイル内容を **インライン展開**（モーダルではなくアコーディオン or パネル展開）
- **metadata_only ソース**: View ボタンは表示しない（ログ内容の Web 閲覧は不可。ユーザーがサーバに直接アクセスして確認する）
- full_import: DB の log_entries から即座に表示
- 行番号表示、severity による色分け
- ページネーション（500 行単位）
- 自動リフレッシュボタン（最新の内容を再取得）

---

## 10. セキュリティ

### 10.1 認証・認可

| リソース | 操作 | 認証要件 |
|---------|------|---------|
| ログソース CUD | POST/PUT/DELETE | **admin のみ** |
| 接続テスト | POST /test | **admin のみ** |
| ファイル一覧・内容閲覧 | GET | 認証必要 |
| ログ検索 | GET | 認証必要 |

### 10.2 認証情報の保護

- パスワードは Fernet 暗号化して DB に保存
- API レスポンスにパスワードを含めない
- ユーザー名はマスク表示（`a****z` 形式）
- 暗号化鍵は環境変数で管理（コードに埋め込まない）

### 10.3 ファイルアクセス制限

- `file_pattern` でアクセス対象ファイルを制限（glob パターン）
- リモートサーバの認証は FTP/SMB プロトコルレベルで実施
- 拡張子制限（要検討: Q&A2 参照）

---

## 11. 設定値

| 設定名 | デフォルト | 説明 | 状態 |
|--------|-----------|------|------|
| `CREDENTIAL_ENCRYPTION_KEY` | (必須) | Fernet 暗号化鍵 | 実装済み |
| `LOG_SOURCE_MIN_POLLING_SEC` | `60` | ポーリング間隔の最小値（秒） | 実装済み（バリデーションのみ） |
| `LOG_SOURCE_MAX_POLLING_SEC` | `300` | ポーリング間隔の最大値（秒） | 実装済み（バリデーションのみ） |
| `LOG_FTP_CONNECT_TIMEOUT` | `30` | FTP 接続タイムアウト（秒） | 実装済み |
| `LOG_FTP_READ_TIMEOUT` | `60` | FTP 読取タイムアウト（秒） | 実装済み（※FTPConnector で受け取るが未適用） |
| `LOG_SCAN_PATH_TIMEOUT` | `300` | パスごとのスキャンタイムアウト（秒、SIGALRM使用） | 実装済み |
| `LOG_SCANNER_ENABLED` | `false` | バックグラウンドスキャナー有効/無効 | 実装済み |
| `LOG_SCANNER_LOOP_INTERVAL` | `30` | スキャナーメインループ間隔（秒） | 実装済み |
| `LOG_ALERT_CONTENT_MAX_LINES` | `200` | alert_on_change 時の 1 ファイルあたり最大読取行数 | 実装済み |
| `LOG_RETENTION_DAYS` | `90` | log_entries の保持日数 | 未実装（Phase 7） |
| `LOG_CONTENT_MAX_LINES` | `500` | コンテンツ取得 API（full_import）の 1 回取得最大行数 | 未実装（Phase 6） |
| `LOG_FILE_MAX_SIZE_MB` | `100` | full_import 対象ファイルサイズ上限（MB） | 未実装（Phase 6） |

> **注記**: `LOG_COLLECTOR_ENABLED` / `LOG_COLLECTOR_LOOP_INTERVAL` / `LOG_ALLOWED_PATHS` は v1 専用設定のため削除済み。未実装の設定値は、対応する Phase 実装時に `app/config.py` に追加する。

---

## 12. 技術選定

### 12.1 ライブラリ

| ライブラリ | 用途 | バージョン | ライセンス |
|-----------|------|----------|-----------|
| `ftplib` | FTP 接続 | Python 標準ライブラリ | PSF |
| `smbprotocol` | SMB 接続 | 1.16.0 | MIT |
| `cryptography` | 認証情報の暗号化 (Fernet) | 46.0.5 | Apache 2.0 / BSD |

### 12.2 requirements.txt 追加

```
smbprotocol==1.16.0
cryptography==46.0.5
```

> `ftplib` は Python 標準ライブラリのため追加不要。

---

## 13. マイグレーション計画

### 13.1 DB マイグレーション

| ステップ | 内容 |
|---------|------|
| 1 | `log_files` テーブル作成 |
| 2 | `log_entries` テーブル作成 |
| 3 | `log_sources` テーブルにカラム追加（access_method, host, port, username, password, base_path, file_pattern, encoding, collection_mode, group_id） |
| 4 | `log_sources` テーブルから不要カラム削除（file_path, last_read_position, last_file_size, system_name, log_type — 段階的に） |
| 5 | 既存 log_sources データの移行（必要に応じて） |

### 13.2 実装フェーズ

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | DB モデル + マイグレーション + ログソース CRUD API | 完了 |
| Phase 2 | リモート接続 (FTP/SMB) + 接続テスト API | 完了 |
| Phase 3 | バックグラウンドスキャナー（メタデータ収集） | **完了** — `app/services/log_scanner.py` 実装済み。`LOG_SCANNER_ENABLED=true` で有効化。`polling_interval_sec` に基づく自動ポーリング対応 |
| Phase 4 | ファイル一覧 API + ソースダッシュボード UI + 手動スキャン + alert_on_change + 当日フィルタ | 完了 |
| Phase 5 | metadata_only メタデータ閲覧（View ボタンなし） | 仕様変更 — metadata_only はオンデマンド参照なし。ファイルメタデータのみ表示、ログ内容は Web UI で閲覧不可 |
| Phase 6 | full_import モード（増分読取 + アラート連携 + ファイルビューア） | 未実装 |
| Phase 7 | 自動クリーンアップ + ログ検索 API | 未実装 |

> **注記**: v1 バックグラウンドコレクター（`log_collector.py`）は v2 アーキテクチャと互換性がないため削除済み。v2 バックグラウンドスキャナー（`log_scanner.py`）は実装済み。

---

## 14. ファイル一覧（予定）

| ファイル | 役割 | 状態 |
|---------|------|------|
| `app/models/log_source.py` | LogSource ORM（リモート接続情報） | 実装済み |
| `app/models/log_source_path.py` | LogSourcePath ORM（監視パス） | 実装済み |
| `app/models/log_file.py` | LogFile ORM（ファイルメタデータ） | 実装済み |
| `app/models/log_entry.py` | LogEntry ORM（ログ行） | 実装済み |
| `app/schemas/log_source.py` | ログソース Pydantic スキーマ | 実装済み |
| `app/schemas/log_file.py` | ファイル Pydantic スキーマ | 実装済み |
| `app/schemas/log_entry.py` | ログエントリ Pydantic スキーマ | 実装済み（未使用） |
| `app/crud/log_source.py` | ログソース CRUD | 実装済み |
| `app/crud/log_source_path.py` | パス CRUD | 実装済み |
| `app/crud/log_file.py` | ファイル CRUD | 実装済み |
| `app/crud/log_entry.py` | エントリ CRUD | 実装済み（未使用） |
| `app/services/log_source_service.py` | ログソースサービス + 手動スキャン | 実装済み |
| `app/services/remote_connector.py` | FTP/SMB 接続抽象化 | 実装済み |
| `app/core/encryption.py` | 認証情報暗号化 | 実装済み |
| `app/routers/api_log_sources.py` | ログソース API ルーター | 実装済み |
| `templates/logs.html` | ログ画面テンプレート | 実装済み |
| `static/js/logs.js` | ログ画面 JavaScript | 実装済み |
| `app/services/log_scanner.py` | バックグラウンドスキャナー | 実装済み |
| `app/services/log_importer.py` | full_import ログ取込 | 未実装（Phase 6） |
| `app/services/log_cleanup.py` | 自動クリーンアップ | 未実装（Phase 7） |
