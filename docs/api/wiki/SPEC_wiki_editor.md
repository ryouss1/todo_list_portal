# WIKI エディタ（Tiptap v2）設計書

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) の補足資料です。
>
> フェーズ1: Tiptap v2 ブロックエディタの初期化・拡張設定・コンテンツ保存

---

## 1. 概要

### 1.1 採用技術

| 項目 | 内容 |
|------|------|
| ライブラリ | **Tiptap v2**（ProseMirror ベースのブロックエディタ） |
| 配信方法 | CDN（esm.sh） または npm ビルド |
| ストレージ形式 | **JSON**（`wiki_pages.content` カラム） |
| フェーズ3拡張 | Yjs + `@tiptap/extension-collaboration`（共同編集、`SPEC_wiki.md` 9.3 参照） |

### 1.2 設計方針

- **フェーズ1**: Tiptap を通常の単一ユーザーエディタとして使用
- **フェーズ3**: `Collaboration` 拡張を後から追加することで共同編集に対応（既存コードの変更を最小化）
- **CDN 優先**: ビルドツール不要で既存の静的ファイル構成に乗せる

---

## 2. 使用拡張（Extensions）

### 2.1 StarterKit 含有拡張（デフォルト有効）

`@tiptap/starter-kit` に含まれる拡張を一括導入する。

| 拡張名 | ブロックタイプ | 説明 |
|--------|--------------|------|
| `Document` | `doc` | ルートノード |
| `Paragraph` | `paragraph` | 通常テキスト |
| `Heading` | `heading` (level 1-6) | 見出し |
| `BulletList` + `ListItem` | `bulletList` | 箇条書きリスト |
| `OrderedList` + `ListItem` | `orderedList` | 番号付きリスト |
| `CodeBlock` | `codeBlock` | コードブロック |
| `Blockquote` | `blockquote` | 引用 |
| `HorizontalRule` | `horizontalRule` | 区切り線 |
| `Bold` | インラインマーク | **太字** |
| `Italic` | インラインマーク | *斜体* |
| `Strike` | インラインマーク | ~~打ち消し線~~ |
| `Code` | インラインマーク | `インラインコード` |
| `History` | - | Undo/Redo（フェーズ3では `CollaborationHistory` に置換） |

### 2.2 追加拡張（フェーズ1）

StarterKit に含まれない拡張を個別追加する。

| 拡張名 | パッケージ | ブロックタイプ | 説明 |
|--------|-----------|--------------|------|
| `Table` + `TableRow` + `TableHeader` + `TableCell` | `@tiptap/extension-table` | `table` | インタラクティブ表 |
| `TaskList` + `TaskItem` | `@tiptap/extension-task-list` | `taskList` | チェックリスト（☑） |
| `Link` | `@tiptap/extension-link` | インラインマーク | URL リンク |
| `Underline` | `@tiptap/extension-underline` | インラインマーク | 下線 |
| `Highlight` | `@tiptap/extension-highlight` | インラインマーク | テキストハイライト |
| `TextAlign` | `@tiptap/extension-text-align` | ノード属性 | 文字寄せ（left/center/right） |
| `Placeholder` | `@tiptap/extension-placeholder` | - | 空エディタ時のプレースホルダー |
| `CharacterCount` | `@tiptap/extension-character-count` | - | 文字数カウント |

### 2.3 フェーズ3 追加拡張（共同編集）

| 拡張名 | パッケージ | 説明 |
|--------|-----------|------|
| `Collaboration` | `@tiptap/extension-collaboration` | Yjs との連携（History 拡張を置き換え） |
| `CollaborationCursor` | `@tiptap/extension-collaboration-cursor` | 他ユーザーのカーソル位置表示 |

---

## 3. フロントエンド実装

### 3.1 CDN インポート（ESM）

```html
<!-- templates/wiki_edit.html の <head> に追加 -->
<script type="importmap">
{
  "imports": {
    "@tiptap/core":                        "https://esm.sh/@tiptap/core@2",
    "@tiptap/starter-kit":                 "https://esm.sh/@tiptap/starter-kit@2",
    "@tiptap/extension-table":             "https://esm.sh/@tiptap/extension-table@2",
    "@tiptap/extension-table-row":         "https://esm.sh/@tiptap/extension-table-row@2",
    "@tiptap/extension-table-header":      "https://esm.sh/@tiptap/extension-table-header@2",
    "@tiptap/extension-table-cell":        "https://esm.sh/@tiptap/extension-table-cell@2",
    "@tiptap/extension-task-list":         "https://esm.sh/@tiptap/extension-task-list@2",
    "@tiptap/extension-task-item":         "https://esm.sh/@tiptap/extension-task-item@2",
    "@tiptap/extension-link":              "https://esm.sh/@tiptap/extension-link@2",
    "@tiptap/extension-underline":         "https://esm.sh/@tiptap/extension-underline@2",
    "@tiptap/extension-highlight":         "https://esm.sh/@tiptap/extension-highlight@2",
    "@tiptap/extension-text-align":        "https://esm.sh/@tiptap/extension-text-align@2",
    "@tiptap/extension-placeholder":       "https://esm.sh/@tiptap/extension-placeholder@2",
    "@tiptap/extension-character-count":   "https://esm.sh/@tiptap/extension-character-count@2"
  }
}
</script>
<script type="module" src="/static/js/wiki.js"></script>
```

### 3.2 エディタ初期化（static/js/wiki.js）

```javascript
// static/js/wiki.js
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableHeader from "@tiptap/extension-table-header";
import TableCell from "@tiptap/extension-table-cell";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Link from "@tiptap/extension-link";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";
import TextAlign from "@tiptap/extension-text-align";
import Placeholder from "@tiptap/extension-placeholder";
import CharacterCount from "@tiptap/extension-character-count";

let editor = null;

function initEditor(initialContent) {
  editor = new Editor({
    element: document.getElementById("wiki-editor"),
    extensions: [
      StarterKit.configure({
        // フェーズ3で Collaboration 拡張と競合するため History は設定可能にしておく
        history: true,
        codeBlock: {
          HTMLAttributes: { class: "wiki-code-block" },
        },
      }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      TaskList,
      TaskItem.configure({ nested: true }),
      Link.configure({ openOnClick: false, autolink: true }),
      Underline,
      Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Placeholder.configure({ placeholder: "ここにコンテンツを入力..." }),
      CharacterCount,
    ],
    content: initialContent || { type: "doc", content: [] },
    onUpdate({ editor }) {
      updateCharCount(editor.storage.characterCount.characters());
    },
  });
}

function updateCharCount(count) {
  const el = document.getElementById("wiki-char-count");
  if (el) el.textContent = `${count} 文字`;
}

// ページ読み込み時に初期化
document.addEventListener("DOMContentLoaded", () => {
  const contentEl = document.getElementById("wiki-initial-content");
  const initialContent = contentEl ? JSON.parse(contentEl.textContent) : null;
  initEditor(initialContent);
});

// 保存
document.getElementById("wiki-save-btn")?.addEventListener("click", savePage);

async function savePage() {
  if (!editor) return;

  const pageId = document.getElementById("wiki-page-id")?.value;
  const title = document.getElementById("wiki-title-input")?.value?.trim();
  const slug = document.getElementById("wiki-slug-input")?.value?.trim();
  const visibility = document.getElementById("wiki-visibility-select")?.value;
  const parentId = document.getElementById("wiki-parent-select")?.value || null;
  const content = editor.getJSON();

  if (!title) {
    showToast("タイトルを入力してください", "warning");
    return;
  }

  const method = pageId ? "PUT" : "POST";
  const url = pageId ? `/api/wiki/pages/${pageId}` : "/api/wiki/pages";

  const body = { title, content, visibility };
  if (slug) body.slug = slug;
  if (parentId) body.parent_id = parseInt(parentId);

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    const page = await res.json();
    showToast("保存しました", "success");
    // 新規作成の場合は編集 URL にリダイレクト
    if (!pageId) {
      window.location.href = `/wiki/${page.slug}/edit`;
    }
  } else {
    const err = await res.json();
    showToast(err.detail || "保存に失敗しました", "danger");
  }
}
```

### 3.3 ツールバー HTML

```html
<!-- templates/wiki_edit.html のツールバー部分 -->
<div id="wiki-toolbar" class="wiki-toolbar">
  <!-- テキストスタイル -->
  <div class="btn-group btn-group-sm me-1">
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleBold().run()" title="太字">
      <i class="bi bi-type-bold"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleItalic().run()" title="斜体">
      <i class="bi bi-type-italic"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleUnderline().run()" title="下線">
      <i class="bi bi-type-underline"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleStrike().run()" title="打ち消し線">
      <i class="bi bi-type-strikethrough"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleCode().run()" title="インラインコード">
      <i class="bi bi-code"></i>
    </button>
  </div>

  <!-- 見出し -->
  <div class="btn-group btn-group-sm me-1">
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleHeading({level:1}).run()">H1</button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleHeading({level:2}).run()">H2</button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleHeading({level:3}).run()">H3</button>
  </div>

  <!-- リスト -->
  <div class="btn-group btn-group-sm me-1">
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleBulletList().run()" title="箇条書き">
      <i class="bi bi-list-ul"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleOrderedList().run()" title="番号付きリスト">
      <i class="bi bi-list-ol"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleTaskList().run()" title="チェックリスト">
      <i class="bi bi-check-square"></i>
    </button>
  </div>

  <!-- ブロック -->
  <div class="btn-group btn-group-sm me-1">
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleCodeBlock().run()" title="コードブロック">
      <i class="bi bi-code-square"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().toggleBlockquote().run()" title="引用">
      <i class="bi bi-blockquote-left"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().insertTable({rows:3,cols:3,withHeaderRow:true}).run()" title="表">
      <i class="bi bi-table"></i>
    </button>
  </div>

  <!-- Undo/Redo -->
  <div class="btn-group btn-group-sm me-1">
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().undo().run()" title="元に戻す">
      <i class="bi bi-arrow-counterclockwise"></i>
    </button>
    <button class="btn btn-outline-secondary" onclick="editor.chain().focus().redo().run()" title="やり直し">
      <i class="bi bi-arrow-clockwise"></i>
    </button>
  </div>

  <span id="wiki-char-count" class="ms-auto text-muted small"></span>
</div>
```

---

## 4. コンテンツの保存・読み込み

### 4.1 JSON ストレージ形式

Tiptap エディタのコンテンツは ProseMirror の **JSON Document** 形式で保存する。

```json
{
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": { "level": 1, "textAlign": "left" },
      "content": [{ "type": "text", "text": "API 設計ガイド" }]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "このドキュメントでは" },
        { "type": "text", "marks": [{ "type": "bold" }], "text": "REST API" },
        { "type": "text", "text": "の設計方針を説明します。" }
      ]
    },
    {
      "type": "codeBlock",
      "attrs": { "language": "python" },
      "content": [{ "type": "text", "text": "def hello():\n    return 'Hello, World!'" }]
    },
    {
      "type": "taskList",
      "content": [
        {
          "type": "taskItem",
          "attrs": { "checked": true },
          "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "完了済みタスク" }] }]
        },
        {
          "type": "taskItem",
          "attrs": { "checked": false },
          "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "未完了タスク" }] }]
        }
      ]
    }
  ]
}
```

### 4.2 テンプレートへの初期コンテンツ埋め込み

Jinja2 テンプレートから JSON を安全に JS に渡す方法:

```html
<!-- templates/wiki_edit.html -->
{% if page %}
<script id="wiki-initial-content" type="application/json">
  {{ page.content | tojson }}
</script>
<input type="hidden" id="wiki-page-id" value="{{ page.id }}">
{% endif %}
```

### 4.3 バックエンドでの JSON バリデーション

Pydantic v2 の `model_validator` で Tiptap JSON の基本構造を検証する。

```python
# app/schemas/wiki_page.py
from pydantic import BaseModel, model_validator
from typing import Optional, Any


class WikiPageCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    parent_id: Optional[int] = None
    content: Optional[dict] = None
    sort_order: int = 0
    visibility: str = "internal"

    @model_validator(mode="before")
    @classmethod
    def set_default_content(cls, values: dict) -> dict:
        if not values.get("content"):
            values["content"] = {"type": "doc", "content": []}
        return values

    @model_validator(mode="after")
    def validate_content(self) -> "WikiPageCreate":
        content = self.content
        if content is not None:
            if not isinstance(content, dict):
                raise ValueError("content must be a JSON object")
            if content.get("type") != "doc":
                raise ValueError("content.type must be 'doc'")
        return self

    @model_validator(mode="after")
    def validate_visibility(self) -> "WikiPageCreate":
        if self.visibility not in ("internal", "public", "private"):
            raise ValueError("visibility must be internal, public, or private")
        return self
```

---

## 5. 読み取り専用表示

ページ閲覧時（`/wiki/{slug}`）は Tiptap を読み取り専用モードで初期化する。

```javascript
// wiki.js - 閲覧モード
function initReadonlyEditor(content) {
  const editor = new Editor({
    element: document.getElementById("wiki-content"),
    extensions: [
      StarterKit,
      Table, TableRow, TableHeader, TableCell,
      TaskList,
      TaskItem.configure({ nested: true }),
      Link,
      Underline,
      Highlight,
      TextAlign,
    ],
    content: content,
    editable: false,  // 読み取り専用
  });
  return editor;
}
```

---

## 6. CSS スタイリング

エディタのコンテンツを適切に表示するための CSS を追加する。

```css
/* static/css/wiki.css */

/* エディタコンテナ */
.wiki-editor-wrapper {
  border: 1px solid var(--bs-border-color);
  border-radius: 0.375rem;
  min-height: 400px;
}

/* Tiptap エディタ本体 */
.ProseMirror {
  padding: 1rem 1.5rem;
  min-height: 400px;
  outline: none;
  font-size: 0.95rem;
  line-height: 1.7;
}

/* 見出し */
.ProseMirror h1 { font-size: 1.8rem; margin: 1.5rem 0 0.75rem; border-bottom: 2px solid var(--bs-border-color); padding-bottom: 0.25rem; }
.ProseMirror h2 { font-size: 1.4rem; margin: 1.25rem 0 0.5rem; }
.ProseMirror h3 { font-size: 1.1rem; margin: 1rem 0 0.5rem; }

/* コードブロック */
.ProseMirror pre {
  background: var(--bs-dark);
  color: var(--bs-light);
  border-radius: 0.375rem;
  padding: 0.75rem 1rem;
  overflow-x: auto;
  font-size: 0.875rem;
}
.ProseMirror code {
  background: rgba(var(--bs-secondary-rgb), 0.15);
  padding: 0.1em 0.3em;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

/* 表 */
.ProseMirror table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.75rem 0;
}
.ProseMirror th, .ProseMirror td {
  border: 1px solid var(--bs-border-color);
  padding: 0.4rem 0.75rem;
  min-width: 60px;
}
.ProseMirror th { background: var(--bs-light); font-weight: 600; }

/* チェックリスト */
.ProseMirror ul[data-type="taskList"] { list-style: none; padding-left: 0; }
.ProseMirror ul[data-type="taskList"] li { display: flex; align-items: flex-start; gap: 0.5rem; }
.ProseMirror ul[data-type="taskList"] input[type="checkbox"] { margin-top: 0.25rem; }

/* 引用 */
.ProseMirror blockquote {
  border-left: 4px solid var(--bs-primary);
  padding: 0.25rem 0 0.25rem 1rem;
  margin: 0.75rem 0;
  color: var(--bs-secondary);
}

/* プレースホルダー */
.ProseMirror p.is-editor-empty:first-child::before {
  content: attr(data-placeholder);
  color: var(--bs-secondary);
  pointer-events: none;
  float: left;
  height: 0;
}

/* ツールバー */
.wiki-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.5rem;
  border-bottom: 1px solid var(--bs-border-color);
  background: var(--bs-light);
  border-radius: 0.375rem 0.375rem 0 0;
}
.wiki-toolbar .btn.is-active {
  background-color: var(--bs-primary);
  color: white;
}
```

---

## 7. フェーズ3 への移行パス

フェーズ1 の Tiptap 実装からフェーズ3（Yjs 共同編集）への移行は最小変更で完了できる。

### 7.1 変更点

**`wiki.js` の変更（約 20 行）:**

```javascript
// フェーズ3 追加インポート
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";

// 1. Yjs ドキュメントとプロバイダを初期化（initEditor の前に追加）
const ydoc = new Y.Doc();
const provider = new WebsocketProvider(
  `ws://${location.host}/ws/wiki`,
  `page-${pageId}`,
  ydoc
);

// 2. Editor 設定の変更
StarterKit.configure({
  history: false,  // ← Collaboration の UndoManager に移行するため無効化
}),
Collaboration.configure({ document: ydoc }),    // ← 追加
CollaborationCursor.configure({                  // ← 追加
  provider,
  user: { name: currentUser, color: "#3b82f6" },
}),
```

**バックエンド追加（新規ファイル）:**

- `app/routers/ws_wiki.py` — WebSocket エンドポイント（`/ws/wiki/{page_id}`）
- `app/services/wiki_collab.py` — Yjs 状態の DB 読み書き

**DB マイグレーション:**

- `wiki_pages.yjs_state`（`BYTEA`）カラムを追加（フェーズ1時点では NULL のまま）

---

## 8. 実装ファイル一覧（エディタ関連）

| ファイル | 種別 | 説明 |
|---------|------|------|
| `static/js/wiki.js` | JS | Tiptap 初期化・ツールバー操作・保存ロジック |
| `static/css/wiki.css` | CSS | エディタ・ツールバー・コンテンツ表示スタイル |
| `templates/wiki_edit.html` | テンプレート | 編集画面（ツールバー + エディタ + 保存ボタン） |
| `templates/wiki.html` | テンプレート | 閲覧画面（読み取り専用 Tiptap + サイドバー） |

---

## 9. テスト方針（エディタ）

エディタ自体（Tiptap JS ライブラリ）のテストは Tiptap 側で担保されているため、アプリ側テストは API 層に集中する。

| テスト | 確認内容 |
|--------|---------|
| JSON コンテンツ保存 | `PUT /api/wiki/pages/{id}` で `content` が正しく保存・取得される |
| 空コンテンツ | `content` が省略された場合、デフォルト値 `{"type":"doc","content":[]}` が設定される |
| 不正 JSON | `content.type` が `"doc"` でない場合に 422 エラー |
| Tiptap JSON ラウンドトリップ | 保存→取得→再保存で値が変化しない |
