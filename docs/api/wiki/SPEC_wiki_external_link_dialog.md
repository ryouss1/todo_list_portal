# Wiki 外部リンク確認ダイアログ 設計書

> 作成日: 2026-02-25 / ステータス: **設計のみ（未実装）**

---

## 1. 概要

Wiki の表示ページ（`/wiki/{slug}`）にて外部リンクをクリックした際に確認ダイアログを表示する機能。
ただし「許可ドメイン（社内ドメイン）」として登録されたドメインはダイアログを表示せず、そのまま遷移する。

---

## 2. 動作方針

| リンク種別 | 動作 |
|-----------|------|
| Wiki 内部リンク（`/wiki/...`） | ダイアログなし・そのまま遷移 |
| アプリ内部リンク（`/` 始まり） | ダイアログなし・そのまま遷移 |
| **許可ドメイン**（社内ドメイン等） | ダイアログなし・新しいタブで遷移 |
| **その他の外部 URL** | **確認ダイアログを表示** |

---

## 3. 許可ドメイン（アローリスト）設計

### 3.1 概念

社内イントラネット・自社サービスなど「安全とみなすドメイン」をあらかじめ登録しておく。
登録済みドメインへのリンクはダイアログをスキップして直接遷移する。

```
例:
  company.internal    → 社内イントラネット
  192.168.0.0/16      → プライベート IP アドレス帯
  backlog.example.com → 社内 Backlog サーバー
  git.example.com     → 社内 Git サーバー
```

### 3.2 DB テーブル設計（新規）

テーブル名: `wiki_allowed_domains`

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| domain | String(253) | NOT NULL, UNIQUE | ドメイン名またはIPアドレス（例: `example.com`） |
| description | String(500) | NULL許可 | 用途メモ（例: 「社内Backlogサーバー」） |
| match_subdomains | Boolean | NOT NULL, DEFAULT true | サブドメインも一致させるか |
| created_by | Integer | FK(users.id, SET NULL), NULL許可 | 登録者 |
| created_at | DateTime(TZ) | DEFAULT now() | 登録日時 |

**`match_subdomains` の挙動例:**

| domain | match_subdomains | マッチする URL の例 |
|--------|-----------------|-------------------|
| `example.com` | true | `https://example.com`, `https://sub.example.com` |
| `example.com` | false | `https://example.com` のみ（`sub.example.com` は不一致） |

### 3.3 マッチングロジック（フロントエンド）

許可ドメイン一覧は API 経由で取得し、JS 側でリンク判定に使用する。

```javascript
function isAllowedDomain(href, allowedDomains) {
    let hostname;
    try {
        hostname = new URL(href).hostname;
    } catch {
        return false;
    }
    return allowedDomains.some(({ domain, match_subdomains }) => {
        if (match_subdomains) {
            return hostname === domain || hostname.endsWith("." + domain);
        }
        return hostname === domain;
    });
}
```

### 3.4 判定フロー

```
外部リンクをクリック
        ↓
href が "/" 始まり？
  → YES: 内部遷移（ダイアログなし）
  → NO: 許可ドメインリストと照合
            ↓
        許可ドメインに一致？
          → YES: 新しいタブで直接遷移（ダイアログなし）
          → NO:  確認ダイアログを表示
```

---

## 4. API 設計

### GET /api/wiki/allowed-domains/
許可ドメイン一覧を取得する（ダイアログ判定用）。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiAllowedDomainResponse[]`

### POST /api/wiki/allowed-domains/
許可ドメインを登録する。

- **権限**: admin のみ
- **リクエストボディ**: `WikiAllowedDomainCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| domain | string | Yes | - | ドメイン名（例: `example.com`） |
| description | string | No | null | 用途メモ |
| match_subdomains | boolean | No | true | サブドメイン一致 |

- **レスポンス**: `201 Created` - `WikiAllowedDomainResponse`
- **エラー**: `409 Conflict` - 重複登録

### DELETE /api/wiki/allowed-domains/{id}
許可ドメインを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### WikiAllowedDomainResponse スキーマ

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | integer | ID |
| domain | string | ドメイン名 |
| description | string \| null | 用途メモ |
| match_subdomains | boolean | サブドメイン一致フラグ |
| created_at | datetime | 登録日時 |

---

## 5. 管理 UI 設計

Wiki 設定画面（または管理者向けの専用画面）に許可ドメイン管理セクションを設ける。

```
┌──────────────────────────────────────────────────────────────┐
│  Wiki 外部リンク 許可ドメイン管理                              │
├──────────────────────────────────────────────────────────────┤
│  説明: 登録済みドメインへのリンクは確認ダイアログをスキップします。  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ドメイン              │ 説明          │ サブドメイン │ 操作│  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ company.internal      │ 社内イントラ  │ ✓           │ 削除│  │
│  │ backlog.example.com   │ 社内Backlog   │ ✗           │ 削除│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────┐  ┌─────────────────────┐            │
│  │ ドメイン名           │  │ 用途メモ             │            │
│  └────────────────────┘  └─────────────────────┘            │
│  [ ] サブドメインも許可する                                    │
│                                          [追加]              │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 確認ダイアログ UI 設計

### 6.1 モーダル仕様

```
┌──────────────────────────────────────────────┐
│  🔗 外部サイトへの移動                     ×  │
├──────────────────────────────────────────────┤
│                                              │
│  以下の外部サイトに移動しようとしています:        │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  https://example.com/page             │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  外部サイトのコンテンツについて、このサイトは   │
│  責任を負いません。                           │
│                                              │
├──────────────────────────────────────────────┤
│              [キャンセル]  [移動する ↗]       │
└──────────────────────────────────────────────┘
```

### 6.2 Bootstrap HTML テンプレート

```html
<!-- 外部リンク確認モーダル（wiki_view.html に追加） -->
<div class="modal fade" id="externalLinkModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content modal-styled">
            <div class="modal-header py-2">
                <h6 class="modal-title">
                    <i class="bi bi-box-arrow-up-right"></i> 外部サイトへの移動
                </h6>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted small mb-2">以下の外部サイトに移動しようとしています:</p>
                <div class="p-2 bg-light rounded text-break small" id="external-link-url"></div>
                <p class="text-muted small mt-2 mb-0">
                    外部サイトのコンテンツについて、このサイトは責任を負いません。
                </p>
            </div>
            <div class="modal-footer py-2">
                <button class="btn btn-secondary btn-sm" data-bs-dismiss="modal">
                    キャンセル
                </button>
                <a id="external-link-proceed" href="#" target="_blank" rel="noopener noreferrer"
                   class="btn btn-primary btn-sm" data-bs-dismiss="modal">
                    移動する <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
        </div>
    </div>
</div>
```

---

## 7. JavaScript 実装方針

### 7.1 起動時に許可ドメイン一覧をキャッシュ

```javascript
class WikiViewer {
    constructor() {
        this.allowedDomains = [];  // キャッシュ
    }

    async init() {
        // 許可ドメイン一覧を取得してキャッシュ
        this.allowedDomains = await wikiApi.getAllowedDomains();
        // ... 他の初期化 ...
        this._setupExternalLinkHandler();
    }

    _setupExternalLinkHandler() {
        document.getElementById("wiki-content").addEventListener("click", (e) => {
            const a = e.target.closest("a.wiki-link-external");
            if (!a) return;
            if (isAllowedDomain(a.href, this.allowedDomains)) return; // スキップ
            e.preventDefault();
            document.getElementById("external-link-url").textContent = a.href;
            document.getElementById("external-link-proceed").href = a.href;
            new bootstrap.Modal(document.getElementById("externalLinkModal")).show();
        });
    }
}
```

### 7.2 API メソッド追加

```javascript
// wikiApi に追加
async getAllowedDomains() {
    const r = await fetch("/api/wiki/allowed-domains/");
    if (!r.ok) return [];
    return r.json();
},
```

---

## 8. 実装スコープ

| ファイル | 変更内容 |
|---------|---------|
| `alembic/versions/xxxx_add_wiki_allowed_domains.py` | `wiki_allowed_domains` テーブル追加 |
| `app/models/wiki_allowed_domain.py` | ORM モデル |
| `app/crud/wiki_allowed_domain.py` | CRUD 操作 |
| `app/schemas/wiki.py` | `WikiAllowedDomainCreate` / `WikiAllowedDomainResponse` スキーマ追加 |
| `app/services/wiki_service.py` | 許可ドメイン管理ロジック追加 |
| `app/routers/api_wiki.py` | `GET /allowed-domains/`, `POST /allowed-domains/`, `DELETE /allowed-domains/{id}` 追加 |
| `templates/wiki_view.html` | 確認モーダル HTML 追加 |
| `templates/wiki_admin.html` (新規) | 許可ドメイン管理 UI |
| `static/js/wiki.js` | `WikiViewer` に許可ドメインキャッシュ + クリックハンドラ追加、`wikiApi.getAllowedDomains()` 追加 |

---

## 9. 既知の制約・考慮事項

| 項目 | 内容 |
|------|------|
| IP アドレス | `company.internal` のような mDNS/NetBIOS 名も登録可能。IP アドレス帯（CIDR）は初期実装では対応しない。 |
| プロトコル判定 | `http://` と `https://` の両方に対応。ドメイン部分のみで照合する。 |
| キャッシュ | 許可ドメイン一覧はページロード時に1回取得してメモリキャッシュ。変更反映はページリロードで対応。 |
| ユーザビリティ | 毎回確認ダイアログを表示するとクリック体験が悪化する場合は「今後 30 日間確認しない（localStorage）」オプションを追加検討する。 |
| アクセシビリティ | Bootstrap モーダルのため Tab/Enter/Escape はフレームワークが対応。 |
