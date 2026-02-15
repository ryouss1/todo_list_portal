# OAuth2/SSO連携 設計書

## 概要

外部認証プロバイダ（Google, GitHub等）によるログインおよびアカウントリンクを提供する。
Authorization Code + PKCE フローを採用。自己登録は不可（管理者が事前にユーザー作成必要）。

---

## 1. アーキテクチャ

### プロバイダ抽象化

```
app/core/auth/oauth/
├── __init__.py        # OAuthUserInfo, get_provider_config re-export
├── provider.py        # OAuthProviderConfig 基底クラス + レジストリ
├── google.py          # Google固有のレスポンスパース
├── github.py          # GitHub固有のレスポンスパース
└── flow.py            # Authorization Code + PKCE フローロジック
```

### データモデル

```python
@dataclass
class OAuthUserInfo:
    provider_user_id: str       # プロバイダ側のユーザーID
    email: Optional[str]        # プロバイダ側のメールアドレス
    display_name: Optional[str] # プロバイダ側の表示名
```

### プロバイダレジストリ

- `OAuthProviderConfig` 基底クラスに `parse_userinfo(data: dict) -> OAuthUserInfo` メソッド
- `register_provider(name, config_class)` で登録、`get_provider_config(name)` で取得
- Google/GitHub はモジュール読み込み時に自動登録

---

## 2. OAuth フロー

### 2.1 ログインフロー

```
[ブラウザ] → GET /api/auth/oauth/google/authorize
         ← 302 → Google認証画面
[Google] → GET /api/auth/oauth/google/callback?code=...&state=...
         ← state検証 → code→token交換 → userinfo取得
         ← ユーザー特定（既存リンク or メール自動リンク）
         ← セッション作成 → 302 /
```

### 2.2 PKCE (Proof Key for Code Exchange)

- `code_verifier`: 43-128文字のランダム文字列
- `code_challenge`: `BASE64URL(SHA256(code_verifier))`（S256方式）
- `code_verifier` は `oauth_states` テーブルに保存

### 2.3 ユーザー特定ロジック

1. **既存リンク検索**: `user_oauth_accounts` で `(provider_id, provider_user_id)` を検索
2. **メール自動リンク**: OAuthメールが `users.email` と一致する場合、自動的にリンクを作成
3. **不一致**: エラー返却（「No matching user found」）

### 2.4 設計判断

| 項目 | 判断 | 理由 |
|------|------|------|
| 自己登録 | 不可 | 既存ポリシー（管理者のみユーザー作成）に準拠 |
| メール自動リンク | 有効 | Google/GitHubはメール検証済み、利便性を優先 |
| PKCE | 採用 | サーバーサイドアプリだが防御の多層化として |
| トークン保存 | DB保存 | 将来のAPI連携に備え（現時点では未使用） |

---

## 3. API エンドポイント

### 3.1 公開エンドポイント (`/api/auth/oauth`)

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/auth/oauth/providers` | 有効プロバイダ一覧（ログインページ用） |
| GET | `/api/auth/oauth/{provider}/authorize` | OAuth認証開始（リダイレクト） |
| GET | `/api/auth/oauth/{provider}/callback` | コールバック処理 |

### 3.2 認証必要エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| DELETE | `/api/auth/oauth/{provider}/unlink` | リンク解除 |
| GET | `/api/auth/oauth/my-links` | リンク一覧 |

### 3.3 管理者エンドポイント (`/api/admin/oauth-providers`)

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/admin/oauth-providers/` | プロバイダ一覧 |
| POST | `/api/admin/oauth-providers/` | プロバイダ作成 |
| PUT | `/api/admin/oauth-providers/{id}` | プロバイダ更新 |
| DELETE | `/api/admin/oauth-providers/{id}` | プロバイダ削除 |

---

## 4. 設定

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `OAUTH_STATE_EXPIRY_SECONDS` | 300 | state有効期限（秒） |
| `OAUTH_CALLBACK_BASE_URL` | `http://localhost:8000` | コールバックベースURL |

---

## 5. セキュリティ考慮事項

- **state パラメータ**: CSRF防止。128文字のランダム文字列、5分有効、使い捨て
- **PKCE**: 認証コード横取り攻撃の防止
- **最後の認証手段保護**: パスワード未設定ユーザーは最後のOAuthリンクを解除不可
- **トークン保存**: `access_token`/`refresh_token` はDB保存（暗号化は将来課題）
- **リンク一意性**: `(provider_id, provider_user_id)` に UNIQUE 制約

---

## 6. ログインページ UI

- `templates/login.html` に OAuth プロバイダボタンを動的表示
- JS が `GET /api/auth/oauth/providers` を呼び出し
- 有効プロバイダごとに「Sign in with {display_name}」ボタンを生成
- クリック時に `/api/auth/oauth/{name}/authorize` にリダイレクト

---

## 7. ファイル一覧

| ファイル | 説明 |
|---------|------|
| `app/core/auth/oauth/__init__.py` | パッケージ初期化 |
| `app/core/auth/oauth/provider.py` | プロバイダ基底クラス + レジストリ |
| `app/core/auth/oauth/google.py` | Google設定 |
| `app/core/auth/oauth/github.py` | GitHub設定 |
| `app/core/auth/oauth/flow.py` | OAuthフローロジック |
| `app/models/oauth_provider.py` | OAuthProvider モデル |
| `app/models/user_oauth_account.py` | UserOAuthAccount モデル |
| `app/models/oauth_state.py` | OAuthState モデル |
| `app/schemas/oauth.py` | Pydantic スキーマ |
| `app/crud/oauth_provider.py` | OAuthProvider CRUD |
| `app/crud/user_oauth_account.py` | UserOAuthAccount CRUD |
| `app/crud/oauth_state.py` | OAuthState CRUD |
| `app/services/oauth_service.py` | ビジネスロジック |
| `app/routers/api_oauth.py` | APIエンドポイント |
| `tests/test_oauth.py` | テスト（22件） |

## 8. テスト

| テストクラス | ケース数 | 内容 |
|-------------|---------|------|
| TestOAuthProviderConfig | 5 | Google/GitHub parse、unknown provider |
| TestOAuthProviderAdmin | 6 | CRUD + disable + non-admin拒否 |
| TestOAuthPublicEndpoints | 3 | 一覧表示、enabled/disabled |
| TestOAuthFlow | 4 | authorize redirect、invalid state、auto-link、unknown email |
| TestOAuthLinking | 4 | my-links、unlink not linked、last method、with linked account |

## 9. 技術的負債

| 項目 | 説明 | 優先度 |
|------|------|--------|
| トークン暗号化 | access_token/refresh_token が平文でDB保存 | 中 |
| トークンリフレッシュ | refresh_token による自動更新が未実装 | 低 |
| プロバイダ追加 | Microsoft/SAML等の追加プロバイダ対応 | 低 |
| OAuth state クリーンアップ | 期限切れ state の定期削除ジョブが未実装 | 低 |
