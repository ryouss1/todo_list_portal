"use strict";

// ─── API helpers ──────────────────────────────────────────────────────────────

const wikiApi = {
    getTree() {
        return api.get("/api/wiki/pages/tree");
    },
    listPages(params = {}) {
        const qs = new URLSearchParams(params).toString();
        return api.get("/api/wiki/pages/?" + qs);
    },
    getPageBySlug(slug) {
        return api.get(`/api/wiki/pages/by-slug/${encodeURIComponent(slug)}`);
    },
    getPageById(pageId) {
        return api.get(`/api/wiki/pages/${pageId}`);
    },
    createPage(data) {
        return api.post("/api/wiki/pages/", data);
    },
    updatePage(pageId, data) {
        return api.put(`/api/wiki/pages/${pageId}`, data);
    },
    deletePage(pageId) {
        return api.del(`/api/wiki/pages/${pageId}`);
    },
    listCategories() {
        return api.get("/api/wiki/categories/");
    },
    createCategory(data) {
        return api.post("/api/wiki/categories/", data);
    },
    deleteCategory(categoryId) {
        return api.del(`/api/wiki/categories/${categoryId}`);
    },
    listTags(q = "") {
        const qs = q ? "?q=" + encodeURIComponent(q) : "";
        return api.get("/api/wiki/tags/" + qs);
    },
    createTag(data) {
        return api.post("/api/wiki/tags/", data);
    },
    updatePageTags(pageId, tagIds) {
        return api.put(`/api/wiki/pages/${pageId}/tags`, { tag_ids: tagIds });
    },
};

// ─── Clipboard helper ─────────────────────────────────────────────────────────

function _fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;left:-9999px;top:-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
        document.execCommand("copy");
        showToast("クリップボードにコピーしました", "success");
    } catch {
        showToast("コピーに失敗しました", "danger");
    }
    document.body.removeChild(ta);
}

// ─── Wiki list page ───────────────────────────────────────────────────────────

class WikiApp {
    constructor() {
        this.categories = [];
        this.selectedCategoryId = null;
    }

    async init() {
        await Promise.all([this.loadTree(), this.loadCategories()]);
        await this.loadPages();
    }

    async loadTree() {
        try {
            const nodes = await wikiApi.getTree();
            this._renderTree(nodes, document.getElementById("wiki-tree"));
        } catch (e) {
            document.getElementById("wiki-tree").innerHTML =
                `<div class="text-danger small p-2">${escapeHtml(e.message)}</div>`;
        }
    }

    _renderTree(nodes, container) {
        if (!nodes.length) {
            container.innerHTML = '<div class="text-muted small p-2">ページなし</div>';
            return;
        }
        const ul = document.createElement("ul");
        ul.className = "list-unstyled mb-0";
        for (const node of nodes) {
            const li = document.createElement("li");
            li.className = "py-1 ps-2";
            li.innerHTML =
                `<a href="/wiki/${escapeHtml(node.slug)}" class="text-decoration-none text-truncate d-block small">`
                + escapeHtml(node.title) + `</a>`;
            ul.appendChild(li);
            if (node.children && node.children.length) {
                const childContainer = document.createElement("div");
                childContainer.className = "ps-3 border-start ms-2";
                this._renderTree(node.children, childContainer);
                li.appendChild(childContainer);
            }
        }
        container.innerHTML = "";
        container.appendChild(ul);
    }

    async loadCategories() {
        try {
            this.categories = await wikiApi.listCategories();
            const sel = document.getElementById("filter-category");
            for (const cat of this.categories) {
                const opt = document.createElement("option");
                opt.value = cat.id;
                opt.textContent = cat.name;
                sel.appendChild(opt);
            }
        } catch (e) {
            console.error("Failed to load categories", e);
        }
    }

    async filterByCategory(categoryId) {
        this.selectedCategoryId = categoryId || null;
        await this.loadPages();
    }

    async loadPages() {
        const container = document.getElementById("wiki-pages-container");
        try {
            const params = {};
            if (this.selectedCategoryId) params.category_id = this.selectedCategoryId;
            const pages = await wikiApi.listPages(params);
            this._renderPages(pages, container);
        } catch (e) {
            container.innerHTML = `<div class="text-danger">${escapeHtml(e.message)}</div>`;
        }
    }

    _renderPages(pages, container) {
        if (!pages.length) {
            container.innerHTML = '<div class="text-muted text-center py-4">ページがありません。「新規ページ」から作成してください。</div>';
            return;
        }
        const rows = pages.map(p => {
            const catBadge = p.category_name
                ? `<span class="badge me-1" style="background:${escapeHtml(p.category_color || "#6c757d")}">${escapeHtml(p.category_name)}</span>`
                : "";
            const tagBadges = (p.tags || []).map(t =>
                `<span class="badge bg-secondary me-1">${escapeHtml(t.name)}</span>`
            ).join("");
            const visBadge = p.visibility === "public"
                ? `<span class="badge bg-success">他部署</span>`
                : p.visibility === "private"
                    ? `<span class="badge bg-danger">非公開</span>`
                    : `<span class="badge bg-secondary">自部署</span>`;
            return `<tr>
                <td><a href="/wiki/${escapeHtml(p.slug)}" class="text-decoration-none fw-semibold">${escapeHtml(p.title)}</a></td>
                <td class="text-muted small">${escapeHtml(p.author_name || "")}</td>
                <td>${catBadge}</td>
                <td>${tagBadges}</td>
                <td>${visBadge}</td>
                <td class="text-muted small">${formatTime(p.updated_at || p.created_at)}</td>
            </tr>`;
        }).join("");
        container.innerHTML = `<div class="table-responsive">
            <table class="table table-hover table-sm align-middle">
                <thead><tr>
                    <th>タイトル</th><th>作成者</th><th>カテゴリ</th><th>タグ</th><th>公開範囲</th><th>更新日時</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
    }

    openCategoryModal() {
        this._renderCategoryList();
        new bootstrap.Modal(document.getElementById("categoryModal")).show();
    }

    _renderCategoryList() {
        const el = document.getElementById("category-list");
        if (!this.categories.length) {
            el.innerHTML = '<div class="text-muted small">カテゴリなし</div>';
            return;
        }
        el.innerHTML = this.categories.map(c =>
            `<div class="d-flex align-items-center justify-content-between mb-1">
                <span><span class="badge me-2" style="background:${escapeHtml(c.color)}">&nbsp;</span>${escapeHtml(c.name)}</span>
                <button class="btn btn-outline-danger btn-sm py-0 px-1" onclick="wikiApp.deleteCategory(${c.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>`
        ).join("");
    }

    async createCategory() {
        const name = document.getElementById("new-cat-name").value.trim();
        const color = document.getElementById("new-cat-color").value;
        if (!name) return;
        try {
            const cat = await wikiApi.createCategory({ name, color });
            this.categories.push(cat);
            document.getElementById("new-cat-name").value = "";
            this._renderCategoryList();
            showToast("カテゴリを作成しました", "success");
        } catch (e) {
            showToast("作成に失敗しました: " + e.message, "danger");
        }
    }

    async deleteCategory(categoryId) {
        if (!confirm("このカテゴリを削除しますか？")) return;
        try {
            await wikiApi.deleteCategory(categoryId);
            this.categories = this.categories.filter(c => c.id !== categoryId);
            this._renderCategoryList();
            showToast("削除しました", "success");
        } catch (e) {
            showToast("削除に失敗しました: " + e.message, "danger");
        }
    }
}

// ─── Wiki page view ───────────────────────────────────────────────────────────

class WikiPageView {
    constructor(slug) {
        this.slug = slug;
        this.page = null;
    }

    async init() {
        const container = document.getElementById("wiki-page-container");
        try {
            this.page = await wikiApi.getPageBySlug(this.slug);
            this._render(container);
        } catch (e) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`;
        }
    }

    _render(container) {
        const p = this.page;
        const catBadge = p.category_name
            ? `<span class="badge me-1" style="background:${escapeHtml(p.category_color || "#6c757d")}">${escapeHtml(p.category_name)}</span>`
            : "";
        const tagBadges = (p.tags || []).map(t =>
            `<span class="badge bg-secondary me-1">${escapeHtml(t.name)}</span>`
        ).join("");
        const breadcrumbs = (p.breadcrumbs || []).map(b =>
            `<li class="breadcrumb-item"><a href="/wiki/${escapeHtml(b.slug)}">${escapeHtml(b.title)}</a></li>`
        ).join("") + `<li class="breadcrumb-item active">${escapeHtml(p.title)}</li>`;

        container.innerHTML = `
            <nav aria-label="breadcrumb" class="mb-3">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="/wiki">Wiki</a></li>
                    ${breadcrumbs}
                </ol>
            </nav>
            <div class="d-flex align-items-start justify-content-between mb-2 flex-wrap gap-2">
                <div>
                    <h4 class="mb-1">${escapeHtml(p.title)}</h4>
                    <div class="d-flex flex-wrap gap-1 align-items-center">
                        ${catBadge}${tagBadges}
                        <span class="text-muted small ms-2">${escapeHtml(p.author_name || "")} &bull; ${formatTime(p.updated_at || p.created_at)}</span>
                    </div>
                </div>
                <a href="/wiki/${escapeHtml(p.slug)}/edit" class="btn btn-outline-secondary btn-sm">
                    <i class="bi bi-pencil"></i> 編集
                </a>
            </div>
            <div class="card">
                <div class="card-body p-0 wiki-content" id="wiki-body"></div>
            </div>`;

        this._renderContent(p.content || "");
    }

    _renderContent(markdown) {
        const el = document.getElementById("wiki-body");
        if (!markdown || !markdown.trim()) {
            el.innerHTML = '<p class="text-muted p-3">内容がありません。</p>';
            return;
        }
        toastui.Editor.factory({
            el,
            viewer: true,
            initialValue: markdown,
            // 内部Wikiは認証ユーザーのコンテンツを信頼するため
            // カスタムクラス・属性を保持できるよう sanitizer を無効化
            customHTMLSanitizer: (html) => html,
        });
        // ビューアーのDOM描画完了後に実行（タイミング問題の回避）
        setTimeout(() => this._setupFilePathCopy(el), 100);
    }

    _setupFilePathCopy(wikiBody) {
        const spans = wikiBody.querySelectorAll("span.wiki-file-path");
        for (const span of spans) {
            // data-path 属性（encodeURIComponent済み）を優先。なければ textContent にフォールバック
            let path = span.dataset.path
                ? decodeURIComponent(span.dataset.path)
                : span.textContent.trim();
            // UNCパスの正規化: マークダウン処理で \\ が \ に化けた場合を補正
            if (path.startsWith("\\") && !path.startsWith("\\\\")) {
                path = "\\" + path;
            }
            // Style the span to look like a file path badge
            span.style.cssText = "display:inline-flex;align-items:center;gap:4px;"
                + "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;"
                + "padding:1px 6px;font-family:monospace;font-size:0.875rem";
            // Prepend folder icon
            const icon = document.createElement("i");
            icon.className = "bi bi-folder2 text-muted";
            icon.style.flexShrink = "0";
            span.prepend(icon);
            // Append copy button
            const btn = document.createElement("button");
            btn.className = "btn btn-link btn-sm p-0 ms-1 text-secondary";
            btn.title = "クリップボードにコピー";
            btn.innerHTML = '<i class="bi bi-clipboard" style="font-size:0.8rem"></i>';
            btn.addEventListener("click", () => {
                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(path).then(() => {
                        showToast("クリップボードにコピーしました", "success");
                    }).catch(() => _fallbackCopy(path));
                } else {
                    _fallbackCopy(path);
                }
            });
            span.appendChild(btn);
        }
    }
}

// ─── Wiki editor ──────────────────────────────────────────────────────────────

class WikiEditor {
    constructor() {
        this.slug = null;
        this.pageId = null;
        this.selectedTagIds = [];
        this.allTags = [];
        this.categories = [];
        this.toastEditor = null;
        this._initialContent = "";
        this._wikiLinkPages = [];
    }

    async init() {
        const container = document.getElementById("wiki-edit-container");
        this.slug = container.dataset.slug || null;
        this.pageId = container.dataset.pageId ? parseInt(container.dataset.pageId) : null;

        await Promise.all([this.loadCategories(), this.loadTags()]);

        if (this.slug) {
            await this.loadExistingPage();
        }
        this._initEditor();
    }

    async loadCategories() {
        try {
            this.categories = await wikiApi.listCategories();
            const sel = document.getElementById("editor-category");
            for (const cat of this.categories) {
                const opt = document.createElement("option");
                opt.value = cat.id;
                opt.textContent = cat.name;
                sel.appendChild(opt);
            }
        } catch (e) {
            console.error("Failed to load categories", e);
        }
    }

    async loadTags() {
        try {
            this.allTags = await wikiApi.listTags();
        } catch (e) {
            console.error("Failed to load tags", e);
        }
    }

    async loadExistingPage() {
        try {
            const page = await wikiApi.getPageBySlug(this.slug);
            this.pageId = page.id;
            document.getElementById("editor-title").value = page.title;
            document.getElementById("editor-slug").value = page.slug;
            document.getElementById("editor-visibility").value = page.visibility || "local";
            document.getElementById("editor-category").value = page.category_id || "";
            document.getElementById("editor-breadcrumb-current").textContent = page.title;
            this.selectedTagIds = (page.tags || []).map(t => t.id);
            this._initialContent = page.content || "";
            this._renderSelectedTags();
        } catch (e) {
            showToast("ページ読み込みに失敗しました: " + e.message, "danger");
        }
    }

    _initEditor() {
        const editorEl = document.getElementById("tiptap-editor");
        if (!editorEl) {
            console.error("Editor element #tiptap-editor not found");
            return;
        }
        if (typeof toastui === "undefined" || !toastui.Editor) {
            editorEl.innerHTML = '<div class="alert alert-warning m-3">エディタライブラリの読み込みに失敗しました。ページを再読み込みしてください。</div>';
            return;
        }
        // Wiki 内部リンク用カスタムツールバーボタン
        const wikiLinkBtn = document.createElement("button");
        wikiLinkBtn.setAttribute("type", "button");
        wikiLinkBtn.className = "toastui-editor-toolbar-icons last";
        wikiLinkBtn.title = "Wiki ページリンク";
        wikiLinkBtn.style.cssText = "background-image:none;font-size:0.95rem;line-height:1";
        wikiLinkBtn.innerHTML = '<i class="bi bi-journal-bookmark"></i>';
        wikiLinkBtn.addEventListener("click", () => this.openWikiLinkPicker());

        // ファイルパス（UNCパス）挿入用カスタムツールバーボタン
        const filePathBtn = document.createElement("button");
        filePathBtn.setAttribute("type", "button");
        filePathBtn.className = "toastui-editor-toolbar-icons last";
        filePathBtn.title = "ファイルパス挿入";
        filePathBtn.style.cssText = "background-image:none;font-size:0.95rem;line-height:1";
        filePathBtn.innerHTML = '<i class="bi bi-folder2"></i>';
        filePathBtn.addEventListener("click", () => this.openFilePathInserter());

        try {
            this.toastEditor = new toastui.Editor({
                el: editorEl,
                height: "500px",
                initialEditType: "wysiwyg",
                previewStyle: "tab",
                initialValue: this._initialContent,
                // 内部Wikiは認証ユーザーのコンテンツを信頼するため sanitizer を無効化
                // （カスタムクラス・data属性を保持して正常に保存できるようにする）
                customHTMLSanitizer: (html) => html,
                toolbarItems: [
                    ["heading", "bold", "italic", "strike"],
                    ["hr", "quote"],
                    ["ul", "ol", "task"],
                    ["table", "link"],
                    ["code", "codeblock"],
                    [
                        { el: wikiLinkBtn, tooltip: "Wiki ページリンク" },
                        { el: filePathBtn, tooltip: "ファイルパス挿入" },
                    ],
                ],
            });
        } catch (e) {
            console.error("Toast UI Editor init failed:", e);
            editorEl.innerHTML = `<div class="alert alert-danger m-3">エディタの初期化に失敗しました: ${escapeHtml(e.message)}</div>`;
        }
    }

    _renderSelectedTags() {
        const container = document.getElementById("editor-selected-tags");
        container.innerHTML = this.selectedTagIds.map(id => {
            const tag = this.allTags.find(t => t.id === id);
            if (!tag) return "";
            return `<span class="badge bg-secondary">
                ${escapeHtml(tag.name)}
                <button type="button" class="btn-close btn-close-white btn-sm ms-1 align-middle"
                    style="font-size:0.5rem"
                    onclick="wikiEditor.removeTag(${id})"></button>
            </span>`;
        }).join("");
    }

    openTagPicker() {
        this.searchTags("");
        new bootstrap.Modal(document.getElementById("tagPickerModal")).show();
    }

    async searchTags(q) {
        try {
            const tags = await wikiApi.listTags(q);
            this.allTags = tags;
            this._renderTagPickerList(tags);
        } catch (e) {
            console.error(e);
        }
    }

    _renderTagPickerList(tags) {
        const container = document.getElementById("tag-picker-list");
        container.innerHTML = tags.map(t => {
            const selected = this.selectedTagIds.includes(t.id);
            return `<span class="badge ${selected ? "bg-primary" : "bg-secondary"} cursor-pointer"
                style="cursor:pointer" onclick="wikiEditor.toggleTag(${t.id})">
                ${escapeHtml(t.name)}
            </span>`;
        }).join("");
    }

    toggleTag(tagId) {
        if (this.selectedTagIds.includes(tagId)) {
            this.selectedTagIds = this.selectedTagIds.filter(id => id !== tagId);
        } else {
            this.selectedTagIds.push(tagId);
        }
        this._renderSelectedTags();
        this._renderTagPickerList(this.allTags);
    }

    removeTag(tagId) {
        this.selectedTagIds = this.selectedTagIds.filter(id => id !== tagId);
        this._renderSelectedTags();
    }

    async createAndAddTag() {
        const name = document.getElementById("new-tag-name").value.trim();
        if (!name) return;
        try {
            const tag = await wikiApi.createTag({ name, color: "#6c757d" });
            this.allTags.push(tag);
            this.selectedTagIds.push(tag.id);
            document.getElementById("new-tag-name").value = "";
            this._renderSelectedTags();
            this._renderTagPickerList(this.allTags);
        } catch (e) {
            showToast("タグ作成に失敗しました: " + e.message, "danger");
        }
    }

    async save() {
        const title = document.getElementById("editor-title").value.trim();
        if (!title) {
            showToast("タイトルを入力してください", "warning");
            return;
        }
        const slugInput = document.getElementById("editor-slug").value.trim();
        const categoryId = document.getElementById("editor-category").value;
        const visibility = document.getElementById("editor-visibility").value;

        const payload = {
            title,
            content: this.toastEditor ? this.toastEditor.getMarkdown() : "",
            visibility,
            category_id: categoryId ? parseInt(categoryId) : null,
            tag_ids: this.selectedTagIds,
        };
        if (slugInput) payload.slug = slugInput;

        try {
            let page;
            if (this.pageId) {
                page = await wikiApi.updatePage(this.pageId, payload);
                showToast("保存しました", "success");
            } else {
                page = await wikiApi.createPage(payload);
                showToast("作成しました", "success");
            }
            window.location.href = `/wiki/${page.slug}`;
        } catch (e) {
            showToast("保存に失敗しました: " + e.message, "danger");
        }
    }

    async openWikiLinkPicker() {
        const listEl = document.getElementById("wiki-link-page-list");
        listEl.innerHTML = '<div class="text-muted small p-2">読み込み中...</div>';
        document.getElementById("wiki-link-search").value = "";
        new bootstrap.Modal(document.getElementById("wikiLinkPickerModal")).show();
        try {
            this._wikiLinkPages = await wikiApi.listPages();
            this._renderWikiLinkPages(this._wikiLinkPages);
        } catch (e) {
            listEl.innerHTML = `<div class="text-danger small p-2">${escapeHtml(e.message)}</div>`;
        }
    }

    filterWikiLinkPages(q) {
        if (!this._wikiLinkPages) return;
        const lower = q.toLowerCase();
        const filtered = q
            ? this._wikiLinkPages.filter(p => p.title.toLowerCase().includes(lower))
            : this._wikiLinkPages;
        this._renderWikiLinkPages(filtered);
    }

    _renderWikiLinkPages(pages) {
        const listEl = document.getElementById("wiki-link-page-list");
        if (!pages.length) {
            listEl.innerHTML = '<div class="text-muted small p-2">ページが見つかりません</div>';
            return;
        }
        listEl.innerHTML = "";
        for (const p of pages) {
            const div = document.createElement("div");
            div.className = "d-flex align-items-center justify-content-between p-2 border-bottom";
            div.style.cursor = "pointer";
            div.innerHTML = `<span class="small fw-semibold">${escapeHtml(p.title)}</span>`
                + `<span class="text-muted small ms-2">/wiki/${escapeHtml(p.slug)}</span>`;
            div.addEventListener("mouseover", () => div.classList.add("bg-light"));
            div.addEventListener("mouseout", () => div.classList.remove("bg-light"));
            div.addEventListener("click", () => this.insertWikiLink(p.slug, p.title));
            listEl.appendChild(div);
        }
    }

    insertWikiLink(slug, title) {
        if (!this.toastEditor) return;
        this.toastEditor.exec("addLink", { linkUrl: `/wiki/${slug}`, linkText: title });
        bootstrap.Modal.getInstance(document.getElementById("wikiLinkPickerModal"))?.hide();
    }

    openFilePathInserter() {
        const input = document.getElementById("file-path-input");
        if (input) input.value = "";
        const modal = new bootstrap.Modal(document.getElementById("filePathModal"));
        document.getElementById("filePathModal").addEventListener("shown.bs.modal", () => {
            if (input) input.focus();
        }, { once: true });
        modal.show();
    }

    insertFilePath() {
        const raw = document.getElementById("file-path-input").value.trim();
        if (!raw || !this.toastEditor) return;
        // HTML特殊文字をエスケープ（表示用）
        const escaped = raw
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
        // data-path にパス原文をURLエンコードして保存
        // （マークダウン処理でバックスラッシュが失われる問題を回避）
        const dataPath = encodeURIComponent(raw);
        const html = `<span class="wiki-file-path" data-path="${dataPath}">${escaped}</span>`;
        const currentMd = this.toastEditor.getMarkdown();
        this.toastEditor.setMarkdown(currentMd + "\n\n" + html + "\n");
        bootstrap.Modal.getInstance(document.getElementById("filePathModal"))?.hide();
    }

    toggleEditorMode() {
        if (!this.toastEditor) return;
        const isMarkdown = this.toastEditor.isMarkdownMode();
        this.toastEditor.changeMode(isMarkdown ? "wysiwyg" : "markdown");
        this._updateModeButton(!isMarkdown);
    }

    _updateModeButton(isMarkdown) {
        const btn = document.getElementById("btn-toggle-mode");
        if (!btn) return;
        btn.innerHTML = isMarkdown
            ? '<i class="bi bi-eye"></i> WYSIWYG'
            : '<i class="bi bi-code-slash"></i> Markdown';
    }

    delete() {
        if (!this.pageId) return;
        const title = document.getElementById("editor-title")?.value.trim() || "このページ";
        const titleDisplay = document.getElementById("delete-page-title-display");
        if (titleDisplay) titleDisplay.textContent = `「${title}」`;
        const confirmBtn = document.getElementById("btn-confirm-delete");
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="bi bi-trash"></i> 削除する';
        }
        new bootstrap.Modal(document.getElementById("deletePageModal")).show();
    }

    async confirmDelete() {
        if (!this.pageId) return;
        const btn = document.getElementById("btn-confirm-delete");
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>削除中...';
        }
        try {
            await wikiApi.deletePage(this.pageId);
            window.location.href = "/wiki";
        } catch (e) {
            showToast("削除に失敗しました: " + e.message, "danger");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-trash"></i> 削除する';
            }
            bootstrap.Modal.getInstance(document.getElementById("deletePageModal"))?.hide();
        }
    }

    cancel() {
        if (this.slug) {
            window.location.href = `/wiki/${this.slug}`;
        } else {
            window.location.href = "/wiki";
        }
    }
}
