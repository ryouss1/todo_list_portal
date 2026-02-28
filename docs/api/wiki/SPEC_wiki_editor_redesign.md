# Wiki エディタ 再設計書

> 作成日: 2026-02-25 / ステータス: **設計書（未実装）**

---

## 1. 現状の問題

### 1.1 現行エディタの課題

| 課題 | 詳細 |
|------|------|
| Markdown貼り付け不可 | `# 見出し` `**太字**` などをペーストしても文字通り表示される |
| Markdown入力不可 | `# ` と入力しても見出しに変換されない |
| 手書き実装の不安定さ | `document.execCommand`（非推奨API）を使用。ブラウザ差異が多い |
| チェックリスト等の不完全さ | 今回修正したように、逐一バグが発生しやすい |

### 1.2 Markdown貼り付け時の現在の挙動

```
ユーザーが以下をコピーしてペースト:

# 見出し1
## 見出し2
**太字テキスト**
- リスト項目

↓ 現在の結果: 全て「文字」として貼り付けられる（Markdown記号ごと）
```

---

## 2. 要件整理

| 要件 | 内容 |
|------|------|
| Markdown貼り付け | MD をペーストすると自動的にリッチテキストに変換される |
| Markdown入力ショートカット | `# ` → H1, `**text**` → 太字, `- ` → リスト など |
| 既存データ互換 | 現行の Tiptap JSON 形式との互換性（移行コスト） |
| CDN 対応 | npm/webpack ビルドなしで動作（現行プロジェクトの制約） |
| Bootstrap 5 共存 | 既存 UI との統一 |
| メンテナンス性 | 自前実装を極力減らす |

---

## 3. ライブラリ比較

### 3.1 比較表

| ライブラリ | タイプ | 保存形式 | Markdown貼り付け | MD入力変換 | CDN対応 | 活発度 |
|-----------|--------|---------|-----------------|-----------|---------|--------|
| **Tiptap v2**（実ライブラリ） | WYSIWYG | Tiptap JSON | ✅ 拡張あり | ✅ InputRules | ✅ esm.sh | ⭐⭐⭐⭐⭐ |
| **Milkdown** | WYSIWYG-MD | Markdown | ✅ ネイティブ | ✅ ネイティブ | ✅ esm.sh | ⭐⭐⭐⭐ |
| **Toast UI Editor** | WYSIWYG+MD 2way | Markdown/HTML | ✅ WYSIWYGモード | ✅ | ✅ CDN | ⭐⭐⭐⭐ |
| **EasyMDE / SimpleMDE** | Markdown（コードエディタ型） | Markdown | ✅（プレーンテキスト） | ✅ | ✅ CDN | ⭐⭐⭐ |
| **CodeMirror 6 + MD** | Markdown（コードエディタ型） | Markdown | ✅（プレーンテキスト） | ✅ | ✅ CDN | ⭐⭐⭐⭐⭐ |
| **現行（手書き）** | WYSIWYG | Tiptap JSON | ❌ | ❌ | - | - |

### 3.2 各ライブラリの詳細

#### Tiptap v2（実ライブラリ）
```
URL: https://tiptap.dev
CDN: https://esm.sh/@tiptap/core, @tiptap/starter-kit, @tiptap/extension-markdown
```
- **特徴**: 現行の「手書き Tiptap 風実装」を置き換える本家ライブラリ
- **Markdown対応**: `@tiptap/extension-markdown` で貼り付け時自動変換・InputRules対応
- **データ互換**: 現行の JSON 形式と完全互換（DB マイグレーション不要）
- **CDN**: ES modules として esm.sh から読み込み可能
- **課題**: esm.sh 経由の CDN 読み込みは依存関係が多く、バンドルサイズが大きい（StarterKit: ~200KB gzip）

#### Milkdown
```
URL: https://milkdown.dev
CDN: https://esm.sh/@milkdown/core 他
```
- **特徴**: Obsidian に最も近い操作感。WYSIWYG で Markdown を扱う
- **Markdown対応**: ネイティブ対応。貼り付け・入力ショートカット完全サポート
- **保存形式**: Markdown テキスト（DB スキーマ変更が必要）
- **課題**: プラグイン式で学習コストが高い。CDN での利用が複雑

#### Toast UI Editor
```
URL: https://ui.toast.com/tui-editor
CDN: https://cdn.jsdelivr.net/npm/@toast-ui/editor/
```
- **特徴**: WYSIWYG ↔ Markdown の切り替えが可能（2 画面モード）
- **Markdown対応**: ネイティブ対応。WYSIWYG でも MD でも操作可能
- **保存形式**: Markdown または HTML（DB スキーマ変更が必要）
- **課題**: 比較的大きめ、モバイル対応が弱い

#### EasyMDE
```
URL: https://easymde.tk
CDN: https://cdn.jsdelivr.net/npm/easymde/dist/
```
- **特徴**: CodeMirror ベースのシンプルな Markdown エディタ。PreviewあとReact不要
- **Markdown対応**: Markdown ソースを直接編集。プレビューはレンダリング表示
- **保存形式**: Markdown テキスト（DB スキーマ変更が必要）
- **操作感**: Obsidian の「ソースモード」に近い。WYSIWYG ではない
- **課題**: リッチな WYSIWYG 体験はない

---

## 4. 推奨案

### 4.1 第一推奨: Toast UI Editor

**理由:**
1. **WYSIWYG ↔ Markdown 切り替え** — Markdown に慣れた人も WYSIWYG 派も両対応
2. **Markdown 貼り付け** — WYSIWYG モードでの貼り付けは自動変換
3. **CDN 対応** — `<script>` + `<link>` タグ1行ずつで導入可能（ESM 不要）
4. **保存形式**: Markdown テキスト（plain text）— DB 移行後は人間が読みやすい形式

```
懸念: DB マイグレーション必要（JSON → TEXT）
対応: 既存 JSON をサーバーサイドで Markdown に変換するスクリプトを実装
```

### 4.2 第二推奨: Tiptap v2（実ライブラリ）

**理由:**
1. **DB マイグレーション不要** — 現行の JSON 形式と完全互換
2. **公式の Markdown 拡張あり** — `@tiptap/extension-markdown` で貼り付け変換・InputRules 完備
3. **Notion ライクな UX** — スラッシュコマンド等に発展可能

```
懸念: CDN 経由で多数の ES modules を読み込む必要あり
対応: Import Map または bundled CDN ビルドを使用
```

### 4.3 比較まとめ

|  | Toast UI Editor | Tiptap v2 |
|--|----------------|-----------|
| **DB 変更** | 必要（JSON → Markdown） | 不要 |
| **CDN 導入** | ◎ `<script>` 1行 | △ ES modules 多数 |
| **Obsidian 感** | ◎ 2モード切替 | ○ WYSIWYG のみ |
| **Markdown 貼り付け** | ✅ | ✅ |
| **保守性** | ✅ 実績あり | ✅ 豊富な拡張 |

---

## 5. Toast UI Editor 実装設計（第一推奨の詳細）

### 5.1 DB スキーマ変更

```
wiki_pages.content: JSON → TEXT (Markdown)
wiki_pages.yjs_state: 削除（リアルタイム共同編集は将来課題）
```

マイグレーションスクリプト（既存 JSON → Markdown 変換）:
```python
# alembic/versions/xxxx_wiki_content_to_markdown.py
# TiptapJSON を Markdown テキストに変換する Python スクリプト
# (tiptap-json-to-md ライブラリ or カスタム変換ロジック)
```

### 5.2 CDN 読み込み（base.html または wiki テンプレート）

```html
<!-- Toast UI Editor -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@toast-ui/editor@3/dist/toastui-editor.min.css">
<script src="https://cdn.jsdelivr.net/npm/@toast-ui/editor@3/dist/toastui-editor-all.min.js"></script>
```

### 5.3 エディタ初期化

```javascript
const editor = new toastui.Editor({
    el: document.getElementById("tiptap-editor"),
    height: "500px",
    initialEditType: "wysiwyg",  // or "markdown"
    previewStyle: "vertical",    // 分割プレビュー
    initialValue: markdownContent,  // 既存 Markdown テキスト
    toolbarItems: [
        ["heading", "bold", "italic", "strike"],
        ["hr", "quote"],
        ["ul", "ol", "task"],
        ["table", "link"],
        ["code", "codeblock"],
    ],
});

// 保存時
const content = editor.getMarkdown();
```

### 5.4 ツールバー対応状況

| 機能 | Toast UI | 現行 |
|------|----------|------|
| 見出し (H1-H6) | ✅ | H1-H3のみ |
| 太字/斜体/取り消し線 | ✅ | ✅ |
| 箇条書き/番号付き | ✅ | ✅ |
| タスクリスト | ✅ | △（バグあり） |
| コードブロック | ✅ | △（バグあり） |
| 引用 | ✅ | ✅ |
| テーブル | ✅ | ❌ |
| 画像添付 | ✅（設定可） | ❌ |
| リンク挿入 | ✅ | ✅ |
| Markdown貼り付け変換 | ✅ | ❌ |
| Markdown入力ショートカット | ✅ | ❌ |
| WYSIWYG / MD 切り替え | ✅ | ❌ |

---

## 6. Tiptap v2 実装設計（第二推奨の詳細）

### 6.1 CDN 読み込み（Import Map 方式）

```html
<script type="importmap">
{
  "imports": {
    "@tiptap/core": "https://esm.sh/@tiptap/core@2",
    "@tiptap/starter-kit": "https://esm.sh/@tiptap/starter-kit@2",
    "@tiptap/extension-markdown": "https://esm.sh/@tiptap/extension-markdown@2"
  }
}
</script>

<script type="module">
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Markdown from "@tiptap/extension-markdown";

const editor = new Editor({
    element: document.getElementById("tiptap-editor"),
    extensions: [
        StarterKit,
        Markdown,   // Markdown 貼り付け自動変換 + InputRules
    ],
    content: existingTiptapJson,  // DB の JSON をそのまま渡せる
});
</script>
```

### 6.2 DB マイグレーション不要

現行の `wiki_pages.content` JSON カラムはそのまま使用可能。

---

## 7. 移行ロードマップ

### Phase 1: ライブラリ選定・POC（今すぐ）
- Toast UI Editor または Tiptap v2 をローカルでプロトタイプ作成
- 実際のデータ（既存 wiki ページ）で動作確認

### Phase 2: 実装（Toast UI を選択した場合）
1. Alembic マイグレーション作成（content: JSON → TEXT）
2. 既存 JSON データを Markdown に変換するマイグレーションスクリプト
3. API: `content` の保存/返却形式を Markdown テキストに変更
4. フロントエンド: `wiki.js` のエディタ部分を Toast UI に置き換え
5. ビュー: Markdown をレンダリング（Toast UI Viewer or marked.js）

### Phase 2: 実装（Tiptap v2 を選択した場合）
1. `wiki.js` のエディタ部分を実 Tiptap に置き換え
2. `@tiptap/extension-markdown` を追加
3. DB 変更なし

---

## 8. 技術的負債

| 項目 | 内容 |
|------|------|
| 現行手書き実装 | `document.execCommand`（非推奨API）使用。早期置き換え推奨 |
| yjs_state カラム | リアルタイム共同編集は未実装のまま空カラムが存在 |
| JSON 形式の Lock-in | Tiptap JSON に依存しており、エディタ変更時に変換コストが発生 |
