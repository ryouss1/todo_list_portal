# 多言語対応（i18n）仕様書

## 1. 概要

Todo List Portal に日本語・英語の2言語対応を追加する。デフォルト言語は日本語とする。

### 1.1 対応範囲

| 対象 | 方式 | 翻訳文字列数（概算） |
|------|------|----------------------|
| Jinja2テンプレート（16ファイル） | サーバーサイド翻訳関数 `_()` | 約400 |
| JavaScript（15ファイル） | クライアントサイド翻訳関数 `i18n.t()` | 約500 |
| Pythonバックエンド（サービス層エラーメッセージ） | サーバーサイド翻訳関数 | 約40 |
| **合計** | | **約940** |

### 1.2 対象外

- データベース内のユーザー入力データ（Todo本文、日報内容、タスク名等）は翻訳しない
- タスクカテゴリマスタ（開発、設計等）はシード値のため翻訳対象外（管理者が手動変更可能）
- ログメッセージ（`logger.info` 等）は英語固定
- WebSocketプロトコルメッセージ（JSONデータ）は翻訳しない

---

## 2. アーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────┐
│  ブラウザ                                            │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ HTML (Jinja2)    │  │ JavaScript               │ │
│  │ {{ _('key') }}   │  │ i18n.t('key')            │ │
│  └──────┬───────────┘  └──────────┬───────────────┘ │
│         │ サーバーサイド翻訳済み     │ クライアントサイド翻訳  │
└─────────┼──────────────────────────┼─────────────────┘
          │                          │
          │  GET /static/locales/{lang}.json
┌─────────┼──────────────────────────┼─────────────────┐
│  サーバー │                          │                  │
│  ┌──────┴───────────┐  ┌──────────┴───────────────┐ │
│  │ i18n Middleware   │  │ static/locales/           │ │
│  │ locale検出→注入   │  │  ├ ja.json                │ │
│  └──────┬───────────┘  │  └ en.json                │ │
│         │               └─────────────────────────┘ │
│  ┌──────┴───────────┐                                │
│  │ app/core/i18n.py │                                │
│  │ 翻訳辞書管理      │                                │
│  └──────────────────┘                                │
└──────────────────────────────────────────────────────┘
```

### 2.2 方式選定

| 検討方式 | 採否 | 理由 |
|----------|------|------|
| gettext (.po/.mo) | 不採用 | 2言語のみには重い、ビルドステップ不要にしたい |
| **JSON辞書 + 自前翻訳関数** | **採用** | シンプル、JS/Pythonで共通形式、保守容易 |
| i18next (JS library) | 不採用 | 外部依存追加が不要なレベルの規模 |

---

## 3. 言語設定

### 3.1 言語の検出と優先順位

言語は以下の優先順位で決定する（上が最優先）：

1. **セッション** — `request.session["lang"]`（言語切替時に設定）
2. **ユーザー設定** — `users.lang` カラム（ログイン時にセッションへコピー）
3. **デフォルト** — `"ja"`（`app/config.py` の `DEFAULT_LANG`）

> `Accept-Language` ヘッダは使用しない（社内ツールのため全員がブラウザ設定を適切に行っているとは限らない）

### 3.2 ユーザーモデル拡張

```python
# app/models.py — User モデルに追加
lang = Column(String(5), nullable=False, server_default="ja")  # "ja" or "en"
```

### 3.3 言語切替API

```
PUT /api/users/me/lang
Content-Type: application/json
{"lang": "en"}

→ 200 {"lang": "en"}
→ 400 {"detail": "Unsupported language: xx"}
```

処理：
1. `users.lang` を更新
2. `request.session["lang"]` を更新
3. レスポンス返却後、フロントがページリロード

### 3.4 言語切替UI

ナビバー右側（ユーザードロップダウンの左）に言語切替ボタンを配置する。

```html
<!-- base.html ナビバー -->
<li class="nav-item">
    <a class="nav-link" href="#" onclick="switchLang()" title="English / 日本語">
        <i class="bi bi-translate"></i>
        <span id="current-lang-label">JA</span>
    </a>
</li>
```

- 現在の言語を `JA` / `EN` で表示
- クリックで他方の言語に切替（トグル動作）
- 切替後にページをリロードして全テキストを反映

---

## 4. バックエンド実装

### 4.1 翻訳モジュール `app/core/i18n.py`

```python
import json
import os
from typing import Dict

SUPPORTED_LANGS = ("ja", "en")
DEFAULT_LANG = "ja"

# メモリ上に辞書をキャッシュ（起動時に1回ロード）
_translations: Dict[str, Dict[str, str]] = {}


def load_translations():
    """static/locales/{lang}.json を読み込み、フラット辞書としてキャッシュ"""
    for lang in SUPPORTED_LANGS:
        path = os.path.join("static", "locales", f"{lang}.json")
        with open(path, "r", encoding="utf-8") as f:
            _translations[lang] = _flatten(json.load(f))


def _flatten(d: dict, prefix: str = "") -> Dict[str, str]:
    """ネストされたJSONをドット区切りのフラットキーに変換"""
    result = {}
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, full_key))
        else:
            result[full_key] = str(value)
    return result


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """翻訳文字列を取得。キーが見つからない場合はキー自体を返す"""
    translations = _translations.get(lang, _translations.get(DEFAULT_LANG, {}))
    text = translations.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_lang(request) -> str:
    """リクエストから言語を取得"""
    lang = request.session.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
```

### 4.2 Jinja2テンプレートへの注入

ミドルウェアで各リクエストに翻訳関数と現在言語を注入する。

```python
# main.py — ミドルウェア追加
from app.core.i18n import t, get_lang

@app.middleware("http")
async def i18n_middleware(request: Request, call_next):
    """リクエストに翻訳関数と言語情報を設定"""
    lang = get_lang(request)
    request.state.lang = lang
    request.state.t = lambda key, **kw: t(key, lang=lang, **kw)
    return await call_next(request)
```

Jinja2テンプレート内では `request.state.t` を使用する。テンプレートグローバルとしてエイリアス `_` を登録する。

```python
# app/routers/pages.py — テンプレート環境設定
from jinja2 import pass_context

@pass_context
def jinja2_translate(context, key, **kwargs):
    request = context["request"]
    return request.state.t(key, **kwargs)

templates.env.globals["_"] = jinja2_translate
templates.env.globals["get_lang"] = lambda ctx: ctx["request"].state.lang
```

### 4.3 テンプレートでの使用例

```html
<!-- 変更前 -->
<h2>Dashboard</h2>
<a class="nav-link" href="/">Dashboard</a>
<button class="btn btn-primary">New Todo</button>

<!-- 変更後 -->
<h2>{{ _('dashboard.title') }}</h2>
<a class="nav-link" href="/">{{ _('nav.dashboard') }}</a>
<button class="btn btn-primary">{{ _('todo.new') }}</button>
```

### 4.4 サービス層エラーメッセージ

サービス層のエラーメッセージは **翻訳キー** を返し、例外ハンドラで翻訳する。

```python
# 変更前（app/services/auth_service.py）
raise AuthenticationError("Invalid email or password")

# 変更後
raise AuthenticationError("error.auth.invalid_credentials")
```

```python
# app/core/exception_handlers.py — 翻訳対応
from app.core.i18n import t, get_lang

async def app_error_handler(request: Request, exc: AppError):
    lang = get_lang(request)
    message = t(exc.message, lang=lang) if exc.message else exc.message
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": message}
    )
```

既存のエラーメッセージ文字列がキーとして見つからない場合はそのまま返すため、段階的な移行が可能。

---

## 5. フロントエンド実装

### 5.1 翻訳ファイル（JavaScript用）

ブラウザからは `GET /static/locales/{lang}.json` で翻訳ファイルを取得する。サーバーサイドと同一ファイルを使用する。

### 5.2 翻訳モジュール `static/js/i18n.js`

```javascript
// i18n — 翻訳モジュール
const i18n = {
    _dict: {},
    _lang: 'ja',

    async init() {
        // base.html で設定された言語を取得
        this._lang = document.documentElement.lang || 'ja';
        try {
            const resp = await fetch(`/static/locales/${this._lang}.json`);
            const data = await resp.json();
            this._dict = this._flatten(data);
        } catch (e) {
            console.error('Failed to load translations:', e);
        }
    },

    t(key, params) {
        let text = this._dict[key] || key;
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                text = text.replace(`{${k}}`, v);
            });
        }
        return text;
    },

    _flatten(obj, prefix) {
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
            const fullKey = prefix ? `${prefix}.${key}` : key;
            if (typeof value === 'object' && value !== null) {
                Object.assign(result, this._flatten(value, fullKey));
            } else {
                result[fullKey] = String(value);
            }
        }
        return result;
    }
};
```

### 5.3 ロード順序

`base.html` の `<script>` 読み込み順序：

```html
<script src="/static/js/common.js"></script>
<script src="/static/js/i18n.js"></script>
<script>
    // i18n を初期化してからページスクリプトを実行
    i18n.init().then(() => {
        document.dispatchEvent(new Event('i18n-ready'));
    });
</script>
<script src="/static/js/api.js"></script>
{% block scripts %}{% endblock %}
```

各ページJSでは、DOM操作を `i18n-ready` イベント後またはそのまま `i18n.t()` を呼ぶ（init完了後に各ページJSが実行されるため）。

### 5.4 JavaScriptでの使用例

```javascript
// 変更前
showToast('Todo created successfully', 'success');
confirm('Delete this todo?');
card.innerHTML = '<span class="badge bg-danger">Urgent</span>';

// 変更後
showToast(i18n.t('todo.msg.created'), 'success');
confirm(i18n.t('todo.confirm.delete'));
card.innerHTML = `<span class="badge bg-danger">${i18n.t('todo.priority.urgent')}</span>`;
```

### 5.5 HTMLテンプレート内のJavaScript

`base.html` 内のインラインスクリプト（パスワード変更等）も `i18n.t()` を使用する。

```javascript
// 変更前
showToast('Password changed successfully', 'success');
errorEl.textContent = 'New passwords do not match';

// 変更後
showToast(i18n.t('auth.msg.password_changed'), 'success');
errorEl.textContent = i18n.t('auth.error.password_mismatch');
```

---

## 6. 翻訳ファイル構造

### 6.1 ファイル配置

```
static/locales/
  ├── ja.json     # 日本語（デフォルト）
  └── en.json     # 英語
```

### 6.2 キー命名規則

```
{機能}.{種別}.{項目}
```

| 種別 | 用途 | 例 |
|------|------|-----|
| `title` | ページタイトル・見出し | `dashboard.title` |
| `nav` | ナビゲーション | `nav.dashboard` |
| `label` | フォームラベル | `todo.label.title` |
| `btn` | ボタン | `todo.btn.create` |
| `msg` | トースト・フィードバック | `todo.msg.created` |
| `confirm` | 確認ダイアログ | `todo.confirm.delete` |
| `error` | エラーメッセージ | `error.auth.invalid_credentials` |
| `status` | ステータス・バッジ | `presence.status.available` |
| `placeholder` | プレースホルダー | `todo.placeholder.title` |
| `th` | テーブルヘッダー | `attendance.th.date` |
| `option` | セレクトボックス選択肢 | `todo.option.priority.high` |

### 6.3 翻訳ファイルサンプル

```json
// static/locales/ja.json
{
  "app": {
    "name": "Todo List Portal"
  },
  "nav": {
    "dashboard": "ダッシュボード",
    "task_list": "タスクリスト",
    "attendance": "勤怠",
    "presence": "在籍状況",
    "tasks": "タスク",
    "reports": "日報",
    "summary": "サマリー",
    "logs": "ログ",
    "alerts": "アラート",
    "users": "ユーザー",
    "todo": "Todo",
    "public_todos": "公開Todo"
  },
  "common": {
    "btn": {
      "save": "保存",
      "cancel": "キャンセル",
      "delete": "削除",
      "edit": "編集",
      "create": "作成",
      "close": "閉じる",
      "search": "検索"
    },
    "label": {
      "title": "タイトル",
      "description": "説明",
      "status": "ステータス",
      "date": "日付",
      "actions": "操作",
      "loading": "読み込み中..."
    },
    "msg": {
      "confirm_delete": "本当に削除しますか？",
      "no_data": "データがありません"
    }
  },
  "auth": {
    "title": "ログイン",
    "label": {
      "email": "メールアドレス",
      "password": "パスワード"
    },
    "btn": {
      "login": "ログイン",
      "logout": "ログアウト",
      "change_password": "パスワード変更"
    },
    "msg": {
      "password_changed": "パスワードを変更しました"
    },
    "error": {
      "password_mismatch": "新しいパスワードが一致しません",
      "login_failed": "ログインに失敗しました"
    }
  },
  "dashboard": {
    "title": "ダッシュボード"
  },
  "todo": {
    "title": "Todoリスト",
    "btn": {
      "new": "新規Todo"
    },
    "label": {
      "title": "タイトル",
      "description": "説明",
      "priority": "優先度",
      "due_date": "期限",
      "visibility": "公開設定"
    },
    "option": {
      "priority": {
        "normal": "通常",
        "high": "高",
        "urgent": "緊急"
      },
      "visibility": {
        "private": "非公開",
        "public": "公開"
      }
    },
    "msg": {
      "created": "Todoを作成しました",
      "updated": "Todoを更新しました",
      "deleted": "Todoを削除しました"
    },
    "confirm": {
      "delete": "このTodoを削除しますか？"
    }
  },
  "attendance": {
    "title": "勤怠管理",
    "btn": {
      "clock_in": "出勤",
      "clock_out": "退勤",
      "break_start": "休憩開始",
      "break_end": "休憩終了",
      "default_set": "デフォルトセット"
    },
    "th": {
      "date": "日付",
      "clock_in": "出勤時刻",
      "clock_out": "退勤時刻",
      "break": "休憩",
      "duration": "勤務時間",
      "input_type": "入力",
      "note": "備考"
    },
    "status": {
      "clocked_in": "出勤中",
      "not_clocked_in": "未出勤",
      "on_break": "休憩中",
      "out": "外出中",
      "meeting": "会議中"
    }
  },
  "task": {
    "title": "タスクタイマー",
    "btn": {
      "new": "新規タスク",
      "start": "開始",
      "stop": "停止",
      "done": "完了"
    },
    "label": {
      "category": "タスク分類",
      "backlog_ticket": "Backlogチケット",
      "report": "日報作成"
    },
    "msg": {
      "created": "タスクを作成しました",
      "started": "タイマーを開始しました",
      "stopped": "タイマーを停止しました",
      "completed": "タスクを完了しました"
    }
  },
  "presence": {
    "title": "在籍状況",
    "status": {
      "available": "在席",
      "away": "離席",
      "out": "外出",
      "break": "休憩",
      "offline": "オフライン",
      "meeting": "会議",
      "remote": "リモート"
    },
    "label": {
      "message": "メッセージ",
      "my_status": "自分のステータス",
      "all_users": "全ユーザー",
      "my_history": "自分の履歴"
    }
  },
  "report": {
    "title": "日報",
    "btn": {
      "new": "新規作成"
    },
    "label": {
      "date": "日付",
      "category": "タスク分類",
      "task_name": "タスク名",
      "time_minutes": "時間（分）",
      "work_content": "作業内容",
      "achievements": "成果",
      "issues": "課題",
      "next_plan": "翌日予定",
      "remarks": "備考"
    },
    "tab": {
      "mine": "自分の日報",
      "all": "全ユーザー"
    }
  },
  "summary": {
    "title": "業務サマリー",
    "period": {
      "daily": "日次",
      "weekly": "週次",
      "monthly": "月次"
    },
    "label": {
      "user_status": "ユーザーレポート状況",
      "report_trends": "レポート推移",
      "category_breakdown": "カテゴリ内訳",
      "issues": "課題"
    }
  },
  "task_list": {
    "title": "タスクリスト",
    "btn": {
      "new": "新規アイテム"
    },
    "section": {
      "unassigned": "未割当",
      "mine": "自分のアイテム"
    },
    "status": {
      "open": "未着手",
      "in_progress": "進行中",
      "done": "完了"
    }
  },
  "user": {
    "title": "ユーザー管理",
    "label": {
      "email": "メールアドレス",
      "display_name": "表示名",
      "role": "ロール",
      "status": "ステータス"
    },
    "role": {
      "admin": "管理者",
      "user": "ユーザー"
    },
    "status": {
      "active": "有効",
      "inactive": "無効"
    }
  },
  "log": {
    "title": "システムログ"
  },
  "alert": {
    "title": "アラート",
    "severity": {
      "info": "情報",
      "warning": "警告",
      "critical": "重大"
    }
  },
  "error": {
    "auth": {
      "invalid_credentials": "メールアドレスまたはパスワードが正しくありません",
      "account_disabled": "アカウントが無効です"
    },
    "not_found": "リソースが見つかりません",
    "conflict": "操作が現在の状態と競合しています",
    "forbidden": "権限がありません",
    "network": "ネットワークエラーが発生しました"
  }
}
```

```json
// static/locales/en.json
{
  "app": {
    "name": "Todo List Portal"
  },
  "nav": {
    "dashboard": "Dashboard",
    "task_list": "Task List",
    "attendance": "Attendance",
    "presence": "Presence",
    "tasks": "Tasks",
    "reports": "Reports",
    "summary": "Summary",
    "logs": "Logs",
    "alerts": "Alerts",
    "users": "Users",
    "todo": "Todo",
    "public_todos": "Public Todos"
  },
  "common": {
    "btn": {
      "save": "Save",
      "cancel": "Cancel",
      "delete": "Delete",
      "edit": "Edit",
      "create": "Create",
      "close": "Close",
      "search": "Search"
    },
    "label": {
      "title": "Title",
      "description": "Description",
      "status": "Status",
      "date": "Date",
      "actions": "Actions",
      "loading": "Loading..."
    },
    "msg": {
      "confirm_delete": "Are you sure you want to delete?",
      "no_data": "No data available"
    }
  },
  "auth": {
    "title": "Login",
    "label": {
      "email": "Email",
      "password": "Password"
    },
    "btn": {
      "login": "Login",
      "logout": "Logout",
      "change_password": "Change Password"
    },
    "msg": {
      "password_changed": "Password changed successfully"
    },
    "error": {
      "password_mismatch": "New passwords do not match",
      "login_failed": "Login failed"
    }
  },
  "dashboard": {
    "title": "Dashboard"
  },
  "todo": {
    "title": "Todo List",
    "btn": {
      "new": "New Todo"
    },
    "label": {
      "title": "Title",
      "description": "Description",
      "priority": "Priority",
      "due_date": "Due Date",
      "visibility": "Visibility"
    },
    "option": {
      "priority": {
        "normal": "Normal",
        "high": "High",
        "urgent": "Urgent"
      },
      "visibility": {
        "private": "Private",
        "public": "Public"
      }
    },
    "msg": {
      "created": "Todo created successfully",
      "updated": "Todo updated successfully",
      "deleted": "Todo deleted successfully"
    },
    "confirm": {
      "delete": "Delete this todo?"
    }
  },
  "attendance": {
    "title": "Attendance",
    "btn": {
      "clock_in": "Clock In",
      "clock_out": "Clock Out",
      "break_start": "Start Break",
      "break_end": "End Break",
      "default_set": "Default Set"
    },
    "th": {
      "date": "Date",
      "clock_in": "Clock In",
      "clock_out": "Clock Out",
      "break": "Break",
      "duration": "Duration",
      "input_type": "Input",
      "note": "Note"
    },
    "status": {
      "clocked_in": "Clocked In",
      "not_clocked_in": "Not Clocked In",
      "on_break": "On Break",
      "out": "Out",
      "meeting": "In Meeting"
    }
  },
  "task": {
    "title": "Task Timer",
    "btn": {
      "new": "New Task",
      "start": "Start",
      "stop": "Stop",
      "done": "Done"
    },
    "label": {
      "category": "Category",
      "backlog_ticket": "Backlog Ticket",
      "report": "Create Report"
    },
    "msg": {
      "created": "Task created",
      "started": "Timer started",
      "stopped": "Timer stopped",
      "completed": "Task completed"
    }
  },
  "presence": {
    "title": "Presence Status",
    "status": {
      "available": "Available",
      "away": "Away",
      "out": "Out",
      "break": "Break",
      "offline": "Offline",
      "meeting": "Meeting",
      "remote": "Remote"
    },
    "label": {
      "message": "Message",
      "my_status": "My Status",
      "all_users": "All Users",
      "my_history": "My History"
    }
  },
  "report": {
    "title": "Daily Reports",
    "btn": {
      "new": "New Report"
    },
    "label": {
      "date": "Date",
      "category": "Category",
      "task_name": "Task Name",
      "time_minutes": "Time (min)",
      "work_content": "Work Content",
      "achievements": "Achievements",
      "issues": "Issues",
      "next_plan": "Next Plan",
      "remarks": "Remarks"
    },
    "tab": {
      "mine": "My Reports",
      "all": "All Reports"
    }
  },
  "summary": {
    "title": "Business Summary",
    "period": {
      "daily": "Daily",
      "weekly": "Weekly",
      "monthly": "Monthly"
    },
    "label": {
      "user_status": "User Report Status",
      "report_trends": "Report Trends",
      "category_breakdown": "Category Breakdown",
      "issues": "Issues"
    }
  },
  "task_list": {
    "title": "Task List",
    "btn": {
      "new": "New Item"
    },
    "section": {
      "unassigned": "Unassigned",
      "mine": "My Items"
    },
    "status": {
      "open": "Open",
      "in_progress": "In Progress",
      "done": "Done"
    }
  },
  "user": {
    "title": "User Management",
    "label": {
      "email": "Email",
      "display_name": "Display Name",
      "role": "Role",
      "status": "Status"
    },
    "role": {
      "admin": "Admin",
      "user": "User"
    },
    "status": {
      "active": "Active",
      "inactive": "Inactive"
    }
  },
  "log": {
    "title": "System Logs"
  },
  "alert": {
    "title": "Alerts",
    "severity": {
      "info": "Info",
      "warning": "Warning",
      "critical": "Critical"
    }
  },
  "error": {
    "auth": {
      "invalid_credentials": "Invalid email or password",
      "account_disabled": "Account is disabled"
    },
    "not_found": "Resource not found",
    "conflict": "Operation conflicts with current state",
    "forbidden": "Forbidden",
    "network": "A network error occurred"
  }
}
```

> 上記はサンプル。実装時に全文字列を網羅した完全版を作成する。

---

## 7. `<html lang>` 属性

テンプレートの `<html lang>` を動的に設定する。

```html
<!-- 変更前 -->
<html lang="ja">

<!-- 変更後 -->
<html lang="{{ request.state.lang }}">
```

これにより `i18n.js` がDOM属性から現在言語を検出できる。

---

## 8. DB マイグレーション

### 8.1 マイグレーション内容

```python
# alembic revision --autogenerate -m "add_lang_to_users"
# users テーブルに lang カラム追加

op.add_column('users', sa.Column('lang', sa.String(5), nullable=False, server_default='ja'))
```

### 8.2 既存データ

既存ユーザーの `lang` は `server_default='ja'` により自動的に `"ja"` が設定される。

---

## 9. ミドルウェアチェーン

言語ミドルウェアの配置順序（上が外側、最初に実行）：

```python
# main.py — ミドルウェア登録順（FastAPIの仕様上、後に追加したものが先に実行）
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)  # 1. セッション復元
# 2. auth_middleware（既存）
# 3. i18n_middleware（新規）— セッションから言語取得
# 4. csrf_middleware（既存）
```

> `i18n_middleware` はセッションアクセスが必要なため、`SessionMiddleware` より後（内側）に配置する。認証前のページ（`/login`）でもデフォルト言語で表示するため、`auth_middleware` の内側に配置。

---

## 10. 実装フェーズ

段階的に移行し、各フェーズで動作確認を行う。

### Phase 1: 基盤構築

1. `app/core/i18n.py` 作成
2. `static/locales/ja.json`、`static/locales/en.json` 作成（共通キー + nav のみ）
3. `static/js/i18n.js` 作成
4. `base.html` に `i18n.js` 読み込み追加
5. i18n ミドルウェア追加
6. Jinja2テンプレートグローバルに `_()` 登録
7. `users.lang` カラム追加（Alembicマイグレーション）
8. `PUT /api/users/me/lang` API追加
9. ナビバーに言語切替ボタン追加
10. `base.html` のナビバーテキストを `_()` で置換
11. テスト追加（言語切替API、翻訳関数）

### Phase 2: テンプレート翻訳

画面単位で順次移行（影響が小さい画面から）：

1. `login.html` — ログイン画面
2. `todos.html`、`todos_public.html` — Todo画面
3. `tasks.html` — タスク画面
4. `presence.html` — 在籍状況画面
5. `reports.html`、`report_detail.html` — 日報画面
6. `attendance.html` — 勤怠画面
7. `task_list.html` — タスクリスト画面
8. `summary.html` — サマリー画面
9. `logs.html` — ログ画面
10. `alerts.html` — アラート画面
11. `users.html` — ユーザー管理画面
12. `index.html`（Dashboard）— ダッシュボード

### Phase 3: JavaScript翻訳

各JSファイルのハードコード文字列を `i18n.t()` で置換：

1. `api.js`、`common.js` — 共通
2. `todos.js`、`todos_public.js`
3. `tasks.js`
4. `presence.js`
5. `reports.js`、`report_detail.js`
6. `attendance.js`
7. `task_list.js`
8. `summary.js`
9. `logs.js`
10. `alerts.js`
11. `users.js`

### Phase 4: バックエンドメッセージ翻訳

1. `app/core/exception_handlers.py` に翻訳処理追加
2. 各サービスのエラーメッセージを翻訳キーに置換
3. テスト更新（エラーメッセージアサーションの修正）

---

## 11. テスト方針

### 11.1 新規テスト

| テスト対象 | テスト内容 |
|-----------|-----------|
| `app/core/i18n.py` | 翻訳関数 `t()` のキー解決、フォールバック、パラメータ置換 |
| `PUT /api/users/me/lang` | 言語切替API（正常系・異常系） |
| 例外ハンドラ | 言語に応じたエラーメッセージの返却 |
| Jinja2 `_()` | テンプレートレンダリングで翻訳が適用されること |

### 11.2 既存テストへの影響

- **エラーメッセージアサーション**: Phase 4でエラーメッセージが翻訳キーに変わるため、テスト側もメッセージ文字列を更新する必要がある
  - 対策: テストは `detail` フィールドの存在確認 + ステータスコード検証を基本とし、メッセージ文字列の完全一致は最小限にする
- **テスト言語**: テスト環境ではセッションに `lang` を設定しないため、デフォルトの `"ja"` が使われる

---

## 12. 設定値

### 12.1 `app/config.py` 追加項目

```python
DEFAULT_LANG = os.environ.get("DEFAULT_LANG", "ja")
SUPPORTED_LANGS = ("ja", "en")
```

### 12.2 環境変数

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `DEFAULT_LANG` | `ja` | デフォルト言語 |

---

## 13. パフォーマンス考慮

| 項目 | 対策 |
|------|------|
| 翻訳辞書ロード | アプリ起動時に1回のみ読み込み、メモリキャッシュ |
| JS翻訳ファイル | ブラウザキャッシュ活用（`?v=` バージョニング） |
| テンプレートレンダリング | dict参照のみのため影響は軽微（<1ms追加） |
| 翻訳ファイルサイズ | 各言語約30KB程度（gzip後 約8KB） |

---

## 14. ファイル一覧（新規・変更）

### 新規作成

| ファイル | 説明 |
|---------|------|
| `app/core/i18n.py` | 翻訳モジュール |
| `static/locales/ja.json` | 日本語翻訳ファイル |
| `static/locales/en.json` | 英語翻訳ファイル |
| `static/js/i18n.js` | JavaScript翻訳モジュール |
| `alembic/versions/xxxx_add_lang_to_users.py` | マイグレーション |
| `tests/test_i18n.py` | i18nテスト |

### 変更

| ファイル | 変更内容 |
|---------|---------|
| `app/config.py` | `DEFAULT_LANG`、`SUPPORTED_LANGS` 追加 |
| `app/models.py` | `User.lang` カラム追加 |
| `app/schemas/user.py` | `lang` フィールド追加 |
| `app/routers/api_users.py` | `PUT /api/users/me/lang` エンドポイント追加 |
| `app/routers/pages.py` | Jinja2グローバル `_()` 登録 |
| `app/core/exception_handlers.py` | 翻訳対応 |
| `main.py` | i18nミドルウェア追加、`load_translations()` 呼び出し |
| `templates/base.html` | `<html lang>` 動的化、i18n.js読み込み、言語切替UI、ナビバー翻訳 |
| `templates/*.html`（全16ファイル） | ハードコード文字列を `_('key')` に置換 |
| `static/js/*.js`（全15ファイル） | ハードコード文字列を `i18n.t('key')` に置換 |
| `app/services/*.py`（該当ファイル） | エラーメッセージを翻訳キーに置換 |
