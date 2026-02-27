# Todo List Portal 仕様書

## 1. 概要

Todo List Portal は、個人・チームの業務効率化を目的とした統合Webポータルアプリケーションである。Todo管理、出勤管理、在籍状態管理、タスク時間追跡、タスクリスト管理、日報管理、業務サマリー、システムログ管理、Wiki知識管理の主要機能を単一のWebアプリケーションとして提供する。

### 1.1 システム構成

| 項目 | 技術 |
|------|------|
| バックエンドフレームワーク | FastAPI 0.115.6 |
| データベース | PostgreSQL 11以上 |
| ORM | SQLAlchemy 2.0.36 |
| バリデーション | Pydantic 2.10.3 |
| テンプレートエンジン | Jinja2 3.1.4 |
| フロントエンド | HTML5 / JavaScript / Bootstrap 5.3.3 |
| アイコン | Bootstrap Icons 1.11.3 |
| リアルタイム通信 | WebSocket (websockets 14.1) |
| アプリケーションサーバー | Uvicorn 0.34.0 |
| DBマイグレーション | Alembic 1.14.1 |
| パスワードハッシュ | passlib[bcrypt] 1.7.4 |
| セッション署名 | itsdangerous 2.2.0 |
| 認証情報暗号化 | cryptography 46.0.5 (Fernet) |
| SMBアクセス | smbprotocol 1.16.0 |
| 国際化(i18n) | Babel 2.16 + gettext |
| CSRF保護 | fastapi-csrf-protect 1.0.7 (Double Submit Cookie) |
| コード品質 | Ruff |
| 言語 | Python 3.9以上 |

### 1.2 アーキテクチャ

レイヤードアーキテクチャを採用し、共通基盤（portal_core）とアプリ固有コードの二層構造で構成される。

```
[フロントエンド (HTML/JS)]
        ↓ HTTP / WebSocket
┌─────────────────────────────────────────────┐
│ portal_core（共通基盤パッケージ）               │
│  認証ミドルウェア → 未認証: /login or 401      │
│  ルーター: api_auth, api_users, api_groups    │
│  テンプレート: base, login, users, forgot/reset_password │
│  静的ファイル: /static/core/                   │
├─────────────────────────────────────────────┤
│ アプリ固有コード（app/）                        │
│  ルーター層 (app/routers/)                     │
│  サービス層 (app/services/)                    │
│  CRUD層 (app/crud/)                           │
│  モデル層 (app/models/)                        │
│  テンプレート: templates/                       │
│  静的ファイル: /static/                         │
└─────────────────────────────────────────────┘
        ↓
[データベース (PostgreSQL)]
```

- **共通基盤** (`portal_core/`): 認証・ユーザー管理・グループ管理・ミドルウェア・テンプレート基盤を提供する再利用可能パッケージ
- **PortalApp ファクトリ**: `main.py` で `PortalApp(config).setup_core()` → `register_*()` → `build()` でアプリを組み立て
- **認証**: セッションベース認証（`SessionMiddleware` + 署名Cookie）— portal_core が提供
- **ルーター層**: HTTPリクエストの受付、バリデーション、レスポンス生成（薄いHTTPラッパー）
- **サービス層**: ビジネスロジック（例外は `NotFoundError`/`ConflictError`/`AuthenticationError`）
- **CRUD層**: データベースへのCRUD操作の実装
- **モデル層**: SQLAlchemyのORMモデル定義
- **スキーマ層** (`app/schemas/`): Pydanticによるリクエスト/レスポンスのデータ構造定義
- **コア層** (`portal_core/portal_core/core/`): 横断的関心事（例外、セキュリティ、依存性注入、ロギング設定）— `app/core/` は再エクスポートshim

---

## 2. 仕様書一覧

| ドキュメント | 内容 |
|-------------|------|
| [db-schema.md](./db-schema.md) | データベース設計（ER図、テーブル定義、カラム仕様） |
| [spec_function.md](./spec_function.md) | 機能一覧・画面仕様・ビジネスロジック |
| [api-design.md](./api-design.md) | API仕様（エンドポイント、リクエスト/レスポンス、WebSocket） |
| [api-design-endpoint.md](./api-design-endpoint.md) | エンドポイント一覧（メソッド・パス・ステータスコード） |
| [spec_nonfunction.md](./spec_nonfunction.md) | 非機能要件・テスト仕様 |
| [spec_roadmap.md](./spec_roadmap.md) | 追加機能ロードマップ（今後の機能追加計画） |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | アーキテクチャ検討書（設計判断・実装フェーズ） |
| [api/auth/security_enhancement.md](./api/auth/security_enhancement.md) | 認証セキュリティ強化設計書（パスワードポリシー、レート制限、ロックアウト、セッション無効化、監査ログ） |
| [api/auth/oauth.md](./api/auth/oauth.md) | OAuth2/SSO連携設計書（Google/GitHub、プロバイダ管理、アカウントリンク） |
| [api/auth/password_reset.md](./api/auth/password_reset.md) | パスワードリセット設計書（トークンベース、SMTP送信） |
| [spec_log_function.md](./spec_log_function.md) | ログ収集機能設計（リモートサーバー接続、スキャン、アラート連携） |
| [spec_log_problem.md](./spec_log_problem.md) | ログ関連 問題点・技術的負債 |
| [spec_wiki.md](./spec_wiki.md) | Wiki機能設計（階層構造、タグ、タスクリンク、Toast UI Editor + Markdown）※実装実績セクション含む |
| [issue7.md](./issue7.md) | 性能・同時アクセス・堅牢性に関する問題点（技術的負債 14件） |

---

## 3. ディレクトリ構造

```
todo_list_portal/
├── main.py                  # エントリーポイント（PortalApp ファクトリ方式）
├── pyproject.toml           # Ruff/pytest設定
├── requirements.txt         # 依存パッケージ
├── alembic.ini              # Alembicマイグレーション設定
├── alembic/versions/        # マイグレーションファイル
├── babel.cfg                # Babel翻訳抽出設定
│
├── portal_core/             # ===== 共通基盤パッケージ =====
│   ├── pyproject.toml       # パッケージ定義
│   └── portal_core/
│       ├── __init__.py      # バージョン情報 (v0.1.0)
│       ├── app_factory.py   # ★ PortalApp ファクトリ + NavItem
│       ├── config.py        # CoreConfig（共通設定）
│       ├── database.py      # SQLAlchemy エンジン・セッション
│       ├── init_db.py       # seed_default_user
│       ├── core/            # 横断的関心事（例外、セキュリティ、DI、ロギング）
│       │   └── auth/        # 認証（パスワードポリシー、レート制限、OAuth）
│       ├── models/          # 共通モデル（User, Group等 8テーブル）
│       ├── crud/            # 共通CRUD（9ファイル）
│       ├── schemas/         # 共通スキーマ（auth, user, group, oauth）
│       ├── services/        # 共通サービス（auth, user, group, oauth, email, ws_manager）
│       ├── routers/         # 共通ルーター（api_auth, api_users, api_groups, api_oauth）
│       ├── templates/       # 共通テンプレート（6ファイル: base, login, users, forgot/reset_password, _dashboard_base）
│       ├── static/          # 共通静的ファイル（→ /static/core/ でマウント）
│       └── tests/           # 共通基盤テスト（158テスト、独立実行可）
│
├── app/                     # ===== アプリ固有コード（+ 再エクスポートshim） =====
│   ├── config.py            # AppConfig(CoreConfig) + globals()後方互換
│   ├── constants.py         # アプリ固有定数
│   ├── database.py          # 再エクスポートshim → portal_core.database
│   ├── init_db.py           # アプリ固有シード（プリセット、カテゴリ）
│   ├── core/                # 再エクスポートshim → portal_core.core/
│   ├── models/              # アプリ固有モデル（33テーブル）+ 共通モデル再エクスポート
│   ├── schemas/             # アプリ固有スキーマ + 共通スキーマ再エクスポート
│   ├── crud/                # アプリ固有CRUD + 共通CRUD再エクスポート
│   ├── routers/             # アプリ固有ルーター（pages.py + api_*.py 19個）
│   └── services/            # アプリ固有サービス + WSマネージャーインスタンス
├── templates/               # アプリ固有ページテンプレート（17ファイル、コアテンプレートの重複なし）
├── static/                  # アプリ固有静的ファイル（→ /static/ でマウント）
│   └── locale/              # フロントエンド翻訳ファイル（JSON）
├── translations/            # バックエンド翻訳ファイル（gettext .po/.mo）
├── scripts/                 # ユーティリティスクリプト（po2json等）
├── tests/                   # pytestテスト（742テスト: コア158 + アプリ584）
└── docs/                    # 仕様書・設計書
```

各ディレクトリの詳細なファイル構成は実際のディレクトリを参照してください。
