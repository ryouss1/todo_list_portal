# Todo List Portal

この資料はこのプロジェクトの使い方と概要を記載している。

## 1. セットアップ

### 1.1 前提条件

| ソフトウェア | バージョン |
|-------------|-----------|
| Python | 3.9以上 |
| PostgreSQL | 11以上 |
| pip | 最新推奨 |

### 1.2 Pythonパッケージのインストール

プロジェクトルートで以下を実行します。

```bash
cd /path/to/todo_list_portal

# 共通基盤パッケージをインストール（編集可能モード）
pip install -e portal_core/

# アプリ依存パッケージをインストール
pip install -r requirements.txt
```

主要な依存パッケージ:

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| fastapi | 0.115.6 | Webフレームワーク |
| uvicorn[standard] | 0.34.0 | ASGIサーバー |
| sqlalchemy | 2.0.36 | ORM |
| psycopg2-binary | 2.9.10 | PostgreSQLドライバ |
| pydantic | 2.10.3 | データバリデーション |
| jinja2 | 3.1.4 | テンプレートエンジン |
| python-multipart | 0.0.18 | フォームデータ処理 |
| websockets | 14.1 | WebSocket通信 |
| alembic | 1.14.1 | DBマイグレーション |
| passlib[bcrypt] | 1.7.4 | パスワードハッシュ |
| itsdangerous | 2.2.0 | セッションCookie署名 |

開発・テスト用に追加で必要なパッケージ:

```bash
pip install pytest httpx ruff
```

> **注意**: `bcrypt` は `4.1` 未満が必要です（`passlib 1.7.4` との互換性）。
> `pip install 'bcrypt<4.1'` で対応してください。

### 1.3 データベースの準備

#### 1.3.1 PostgreSQLデータベースの作成

PostgreSQLに接続し、データベースを作成します。

```bash
psql -U postgres -h postgres-11-test
```

```sql
CREATE DATABASE todo_list_portal;
```

#### 1.3.2 接続情報の設定

プロジェクトルートの **`.env`** ファイルでデータベースの接続URLを設定します。

> **注意**: `.env` ファイルは `.gitignore` に登録済みです。パスワード等の機密情報を確認する際は `.env` ファイルを直接参照してください。

```bash
# .env ファイルの例
DATABASE_URL=postgresql://<ユーザー名>:<パスワード>@<ホスト名>/<データベース名>
SECRET_KEY=<セッション署名キー>
DEFAULT_PASSWORD=<初期ユーザーパスワード>
```

`.env` ファイルが存在しない場合は、`.env` ファイルを新規作成し、上記の環境変数を設定してください。
`app/config.py` は `python-dotenv` により `.env` を自動読み込みします。

#### 1.3.3 マイグレーションの適用

テーブルの作成・変更は Alembic で管理されています。

```bash
# マイグレーションの適用（初回セットアップ時も同じコマンド）
alembic upgrade head
```

起動時に以下の処理が実行されます:
- デフォルトユーザー（id=1, email=`admin@example.com`）が存在しない場合に作成（パスワードは `.env` の `DEFAULT_PASSWORD`）
- 既存ユーザーにパスワードが未設定の場合、デフォルトパスワードを設定

---

## 2. サーバーの起動

### 2.1 開発環境での起動

#### 方法1: main.pyから起動（推奨）

```bash
cd /path/to/todo_list_portal
python main.py
```

この方法で起動した場合の設定:
- ホスト: `0.0.0.0`（全インターフェースで待ち受け）
- ポート: `8000`
- ホットリロード: 有効（ファイル変更時に自動再起動）

#### 方法2: uvicornコマンドで起動

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2.2 本番環境での起動

本番環境ではホットリロードを無効にし、ワーカー数を指定して起動します。

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

バックグラウンドで起動する場合:

```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > /dev/null 2>&1 &
```

### 2.3 起動の確認

起動後、以下のURLにアクセスして動作を確認します。

| URL | 説明 |
|-----|------|
| `http://<ホスト>:8000/` | Dashboard画面（要ログイン） |
| `http://<ホスト>:8000/login` | ログイン画面 |
| `http://<ホスト>:8000/docs` | Swagger UI（API仕様の確認・テスト） |
| `http://<ホスト>:8000/redoc` | ReDoc（API仕様の閲覧） |

**デフォルトログイン情報:**

| 項目 | 値 |
|------|-----|
| メールアドレス | `admin@example.com`（環境変数 `DEFAULT_EMAIL` で変更可能） |
| パスワード | `.env` ファイルの `DEFAULT_PASSWORD` を参照 |

### 2.4 サーバーの停止

#### フォアグラウンドで実行中の場合

`Ctrl + C` で停止します。

#### バックグラウンドで実行中の場合

```bash
# プロセスを検索
ps aux | grep uvicorn

# PIDを指定して停止
kill <PID>
```

### 2.5 WSL2環境でのアクセス

WSL2（Windows Subsystem for Linux 2）上でサーバーを起動した場合、`0.0.0.0` でバインドしてもWindowsホスト側から直接アクセスできない場合があります。WSL2は仮想マシンとして動作するため、ネットワークが分離されています。

#### 方法1: localhost経由（推奨）

WSL2のデフォルト設定では `localhostForwarding` が有効になっており、Windowsホストから `localhost` でアクセスできます。

```
http://localhost:8000
```

#### 方法2: WSL2のIPアドレスを直接指定

`localhost` でアクセスできない場合、WSL2のIPアドレスを確認して直接アクセスします。

```bash
# WSL2のIPアドレスを確認
hostname -I
# 例: 192.168.69.187
```

```
http://192.168.69.187:8000
```

> **注意**: WSL2のIPアドレスはWSL再起動のたびに変わる可能性があります。

#### 方法3: localhostForwardingの設定確認

方法1で接続できない場合、Windowsホスト側の設定ファイル `%USERPROFILE%\.wslconfig` を確認・作成します。

```ini
[wsl2]
localhostForwarding=true
```

設定変更後、PowerShellで以下を実行してWSLを再起動します。

```powershell
wsl --shutdown
```

#### 接続確認

WSL2内部からサーバーが正常に動作しているか確認するには:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login
# 200 が返れば正常
```

---

## 3. メンテナンス

### 3.1 ログ管理

#### アプリケーションログ

ログファイルはプロジェクトルートの `app.log` に出力されます。

| 設定項目 | 値 |
|---------|-----|
| ファイルパス | `./app.log` |
| 最大サイズ | 10MB / ファイル |
| ローテーション | 最大5ファイル（`app.log`, `app.log.1` 〜 `app.log.5`） |
| 出力先 | ファイル + コンソール（stdout） |
| フォーマット | `YYYY-MM-DD HH:MM:SS [LEVEL] logger_name: message` |

ログの確認:

```bash
# 最新のログを確認
tail -f app.log

# エラーログのみ抽出
grep "\[ERROR\]" app.log

# 特定日時のログを検索
grep "2026-02-09" app.log
```

ログファイルの手動クリア（必要な場合）:

```bash
# ログファイルを空にする（サーバー稼働中でも可）
truncate -s 0 app.log
```

#### システムログ（logsテーブル）

アプリケーション内のログ機能（`/api/logs/`）で記録されるログは、データベースの`logs`テーブルに保存されます。件数が増加した場合は、以下のSQLで古いログを削除できます。

```sql
-- 30日以上前のログを削除
DELETE FROM logs WHERE received_at < NOW() - INTERVAL '30 days';
```

### 3.2 データベースメンテナンス

#### テーブル定義の確認

テーブルの定義は共通基盤（`portal_core/portal_core/models/`）とアプリ固有（`app/models/`）の二層で管理されています。詳細は [db-schema.md](./db-schema.md) を参照してください。

| 分類 | テーブル数 | モデル定義 |
|------|----------|-----------|
| 共通基盤（認証・ユーザー・グループ） | 8 | `portal_core/portal_core/models/` |
| アプリ固有（Todo・勤怠・タスク等） | 26 | `app/models/` |
| **合計** | **34** | |

#### スキーマ変更時の対応

スキーマの変更は Alembic で管理します。

1. `app/models/` 配下のモデルファイルを修正
2. 対応する `app/schemas/` のスキーマファイルを修正
3. マイグレーションを自動生成・適用

```bash
# モデル変更からマイグレーションを自動生成
alembic revision --autogenerate -m "変更内容の説明"

# マイグレーションの適用
alembic upgrade head

# ロールバック（1つ前に戻す）
alembic downgrade -1
```

#### データベースのバックアップ

```bash
# バックアップ
pg_dump -U postgres -h postgres-11-test todo_list_portal > backup_$(date +%Y%m%d).sql

# リストア
psql -U postgres -h postgres-11-test todo_list_portal < backup_20260209.sql
```

#### データベースのリセット

テスト環境などでデータを完全にリセットする場合:

```bash
psql -U postgres -h postgres-11-test
```

```sql
-- データベースを削除して再作成
DROP DATABASE todo_list_portal;
CREATE DATABASE todo_list_portal;
```

再作成後、`alembic upgrade head` を実行し、アプリケーションを起動すればデフォルトユーザーが自動的に作成されます。

### 3.3 テストの実行

テストはデータベースに接続して実行されますが、各テストはトランザクション内で実行され、テスト後にロールバックされるため、既存データには影響しません。

```bash
# portal_core 単体テスト（151件）
cd portal_core && pytest tests/ -q

# アプリテスト（500件）
pytest tests/ -q

# 全テスト（CI用）
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q

# 詳細出力付き
pytest tests/ -v

# 特定のテストファイルを実行
pytest tests/test_todos.py
pytest tests/test_attendances.py

# 特定のテストケースを実行
pytest tests/test_todos.py::TestTodoAPI::test_create_todo
```

### 3.4 コード品質チェック

Ruff を使用したリンティングとフォーマットの実行:

```bash
# リントチェック
ruff check .

# リント自動修正
ruff check --fix .

# フォーマット
ruff format .
```

設定は `pyproject.toml` で管理されています（`line-length=120`, Python 3.9対象）。

### 3.5 依存パッケージの更新

```bash
# 現在のパッケージバージョンを確認
pip list

# パッケージを更新する場合はrequirements.txtを編集後に実行
pip install -r requirements.txt --upgrade
```

> **注意**: パッケージ更新後はテストを実行して動作を確認してください。

### 3.6 トラブルシューティング

#### サーバーが起動しない

| 症状 | 原因 | 対処 |
|------|------|------|
| `ModuleNotFoundError` | 依存パッケージ未インストール | `pip install -r requirements.txt` を実行 |
| `connection refused` (DB接続エラー) | PostgreSQLが起動していない、または接続情報が誤り | PostgreSQLの起動確認と `.env` ファイルの `DATABASE_URL` を確認 |
| `Address already in use` | ポート8000が使用中 | 別ポートで起動するか、使用中のプロセスを停止 |

#### データベース関連のエラー

| 症状 | 原因 | 対処 |
|------|------|------|
| `database "todo_list_portal" does not exist` | データベース未作成 | PostgreSQLで `CREATE DATABASE todo_list_portal;` を実行 |
| `relation "xxx" does not exist` | テーブル未作成 | アプリケーションを一度起動して自動作成させる |
| `FATAL: password authentication failed` | DB認証情報の誤り | `.env` ファイルの `DATABASE_URL` のユーザー名・パスワードを確認 |

#### ポートの確認

```bash
# ポート8000を使用しているプロセスを確認
lsof -i :8000

# または
ss -tlnp | grep 8000
```
