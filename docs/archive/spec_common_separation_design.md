# 共通機能分離 設計詳細（アーカイブ）

> このファイルは `spec_common_separation.md` から分離したアーカイブです。
> フェーズ1・2で実装完了済みの設計内容を保存しています。
> 現行の設計書は [spec_common_separation.md](../spec_common_separation.md) を参照してください。

---

## 1. ディレクトリ構造（将来構想）

```
workspace/                              # モノレポルート
│
├── portal_core/                        # ===== 共通基盤パッケージ =====
│   ├── pyproject.toml                  # パッケージ定義
│   ├── portal_core/
│   │   ├── __init__.py                 # バージョン情報
│   │   ├── app_factory.py             # ★ 核心: PortalApp ファクトリ
│   │   ├── config.py                  # 共通設定（DB, SECRET_KEY, i18n等）
│   │   ├── database.py                # SQLAlchemy エンジン・セッション
│   │   ├── init_db.py                 # seed_default_user のみ
│   │   ├── core/                      # 横断的関心事
│   │   │   ├── deps.py, exceptions.py, exception_handlers.py
│   │   │   ├── security.py, encryption.py, i18n.py
│   │   │   ├── logging_config.py, utils.py
│   │   │   └── auth/                  # 認証サブシステム
│   │   │       ├── audit.py, password_policy.py, rate_limiter.py
│   │   │       └── oauth/ (flow.py, provider.py, google.py, github.py)
│   │   ├── models/                    # 共通モデル（8テーブル）
│   │   ├── crud/                      # 共通CRUD（9ファイル）
│   │   ├── schemas/                   # 共通スキーマ（4ファイル）
│   │   ├── services/                  # 共通サービス（7ファイル）
│   │   ├── routers/                   # 共通ルーター（4ファイル）
│   │   ├── templates/                 # 共通テンプレート（6ファイル）
│   │   ├── static/                    # 共通静的ファイル（6ファイル）
│   │   └── translations/             # 共通翻訳ファイル
│   └── tests/                         # 共通基盤のテスト
│
├── apps/
│   ├── todo_portal/                   # Todo List Portal アプリ
│   └── inventory_app/                 # 別アプリ（将来例）
└── README.md
```

---

## 2. PortalApp ファクトリ設計（実装済み）

> 実装コード: `portal_core/portal_core/app_factory.py` (~280行)

PortalApp クラスが以下を提供:
- `setup_core()`: ミドルウェア（Session, CSRF, Auth, Locale）、コアルーター、コアナビ項目を一括登録
- `register_router/nav_item/page/websocket()`: アプリ側からの拡張ポイント
- `build()`: Jinja2環境構築、静的ファイルマウント、ページ/WSルート登録を実行

### portal_core 単体で使える機能

| 機能 | エンドポイント |
|------|-------------|
| ログイン画面 | `GET /login` |
| ログイン/ログアウト API | `POST /api/auth/login`, `/logout` |
| OAuth認証 | `GET /api/auth/oauth/*` |
| パスワードリセット | `POST /api/auth/forgot-password` |
| ユーザー管理画面 | `GET /users` |
| ユーザー/グループ API | `/api/users/*`, `/api/groups/*` |
| Dashboard | `GET /` |

---

## 3. base.html 動的ナビゲーション（実装済み）

ハードコードされた14項目 → `{% for item in nav_items %}` ループに置換。
`register_nav_item()` で項目を登録するだけでナビバーに自動反映。

---

## 4. テンプレートと静的ファイルの解決（実装済み）

- テンプレート優先順位: アプリ側 `templates/` > portal_core `templates/`（FileSystemLoader）
- 静的ファイル: コア → `/static/core/`、アプリ固有 → `/static/`

---

## 5. 設定の継承（実装済み）

`CoreConfig`（共通設定: DB, Auth, i18n等）→ `AppConfig(CoreConfig)`（アプリ固有設定）のクラス継承構造。
`.env` ファイルは1つ。`globals()` ループで後方互換維持。

---

## 6. Alembic マイグレーション（実装済み）

- 共通テーブルとアプリ固有テーブルは同一DB・同一マイグレーションチェーン
- `env.py` で `portal_core.models` + `app.models` を両方インポート

---

## 7. 開発ワークフロー

```bash
# 初期セットアップ
pip install -e portal_core/
pip install -r requirements.txt
alembic upgrade head
python main.py

# アプリ固有機能追加
# 1. app/{models,crud,schemas,services,routers}/ にファイル追加
# 2. main.py で register_router(), register_page(), register_nav_item()
# 3. templates/, static/js/ にUI追加
# 4. alembic revision --autogenerate → pytest tests/ -q
```

---

## 8. 移行計画（概要版）

| フェーズ | 作業数 | 状態 |
|---------|-------|------|
| フェーズ1: 準備リファクタリング | 9作業 | ✅ 完了 |
| フェーズ2: パッケージ作成・移動 | 18作業 | ✅ 完了 |
| フェーズ3: テスト分離・安定化 | 11作業 | ⏳ 未着手 |

---

## 9. メリット・デメリット

### メリット
- 認証の再実装不要（`setup_core()` だけで認証・ユーザー管理が使える）
- セキュリティパッチの一元管理
- 品質の均一化（全アプリで同じ認証・CSRF・ロギング・i18n）
- 漸進的移行（段階的に移行でき、既存の動作を壊すリスクが低い）

### デメリット
- バージョン管理が暗黙的（portal_core の変更が即全アプリに影響）
- テスト実行時間（portal_core + アプリの両方をテスト）

---

## 10. FAQ

**Q: portal_core 単体では認証なしで動くの？**
いいえ。`setup_core()` で認証が全て組み込まれる。

**Q: 共通テーブルとアプリテーブルは同じDBに入る？**
はい。同一 `DATABASE_URL` を共有し、FK制約がそのまま機能する。

**Q: 将来、別リポジトリに分けたくなったら？**
`pip install -e ../portal_core/` を `pip install portal-core>=1.0` に変えるだけ。

**Q: ユーザーモデルにアプリ固有のカラムを追加したい場合は？**
1. リレーション拡張: `user_settings` テーブルで1:1関連（推奨）
2. mixin: User モデル継承（Alembic注意）
