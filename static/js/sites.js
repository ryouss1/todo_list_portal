'use strict';

// State
let allLinks = [];
let allGroups = [];
let isAdmin = false;
let currentUserId = 0;
let ws = null;

// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const me = await api.get('/api/auth/me');
        isAdmin = me.role === 'admin';
        currentUserId = me.user_id;
    } catch (e) { /* unauthenticated */ }

    if (isAdmin) {
        document.getElementById('btn-add-group').classList.remove('d-none');
    }

    await loadSites();
    connectWebSocket();
});

// ── Data loading ────────────────────────────────────────────────────────────

async function loadSites() {
    try {
        const [links, groups] = await Promise.all([
            api.get('/api/sites/'),
            api.get('/api/site-groups/'),
        ]);
        allLinks = links;
        allGroups = groups;
        renderPage();
    } catch (e) {
        document.getElementById('sites-container').innerHTML =
            `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`;
    }
}

// ── Render ───────────────────────────────────────────────────────────────────

function renderPage() {
    const container = document.getElementById('sites-container');
    if (allLinks.length === 0 && allGroups.length === 0) {
        container.innerHTML = '<div class="text-muted text-center py-5">登録されたサイトがありません。[+ Add Link] から追加してください。</div>';
        return;
    }

    const sections = [];

    // Grouped sections
    for (const group of allGroups) {
        const groupLinks = allLinks.filter(l => l.group_id === group.id);
        sections.push(renderGroupSection(group, groupLinks));
    }

    // Ungrouped section
    const ungrouped = allLinks.filter(l => l.group_id === null);
    if (ungrouped.length > 0) {
        sections.push(renderGroupSection(null, ungrouped));
    }

    container.innerHTML = sections.join('');

    // Attach Bootstrap Tooltips to cards with description
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el, { trigger: 'hover', placement: 'top' });
    });
}

function renderGroupSection(group, links) {
    const groupColor = group ? escapeHtml(group.color) : '#6c757d';
    const groupName = group ? escapeHtml(group.name) : '未分類';
    const groupIcon = group && group.icon ? `<i class="bi ${escapeHtml(group.icon)} me-1"></i>` : '';
    const groupId = group ? group.id : null;

    const editGroupBtn = isAdmin && group
        ? `<button class="btn btn-outline-secondary btn-sm py-0 px-1" onclick="openGroupModal(${group.id})" title="グループ編集"><i class="bi bi-pencil" style="font-size:0.75rem"></i></button>`
        : '';
    const addLinkBtn = `<button class="btn btn-link btn-sm py-0 px-1 text-primary" style="font-size:0.78rem" onclick="openLinkModal(null, ${groupId || 'null'})" title="このグループにリンクを追加"><i class="bi bi-plus-circle"></i> 追加</button>`;

    const cardsHtml = links.map(l => renderCard(l)).join('');
    const emptyHtml = links.length === 0
        ? '<div class="text-muted small fst-italic ms-1">リンクがありません</div>'
        : '';

    return `
<div class="site-group-section">
    <div class="site-group-header">
        <span class="site-group-dot" style="background-color:${groupColor}"></span>
        ${groupIcon}${groupName}
        <div class="group-actions">
            ${editGroupBtn}
            ${addLinkBtn}
        </div>
    </div>
    <div class="site-cards-grid">
        ${cardsHtml}
        ${emptyHtml}
    </div>
</div>`;
}

function renderCard(link) {
    const statusClass = escapeHtml(link.status);
    const dotHtml = `<span class="status-dot ${statusClass}" title="${escapeHtml(link.status)}"></span>`;
    const statusText = `<span class="status-text ${statusClass}">${escapeHtml(link.status.toUpperCase())}</span>`;

    const responseTime = (link.status === 'up' && link.response_time_ms !== null)
        ? `<div>${link.response_time_ms}ms</div>` : '';
    const lastChecked = link.last_checked_at
        ? `<div>${formatRelativeTime(link.last_checked_at)}</div>`
        : `<div class="fst-italic">未確認</div>`;

    const canEdit = isAdmin || link.created_by === currentUserId;
    const actionBtns = canEdit ? `
        <div class="card-actions">
            <button class="btn btn-outline-secondary btn-sm" onclick="event.stopPropagation(); openLinkModal(${link.id})" title="編集"><i class="bi bi-pencil" style="font-size:0.7rem"></i></button>
            <button class="btn btn-outline-danger btn-sm" onclick="event.stopPropagation(); deleteLink(${link.id})" title="削除"><i class="bi bi-trash" style="font-size:0.7rem"></i></button>
        </div>` : '';

    const tooltipAttr = link.description
        ? `data-bs-toggle="tooltip" data-bs-title="${escapeHtml(link.description)}"`
        : '';

    return `
<div class="card site-card status-${statusClass}" id="card-${link.id}"
     onclick="navigateToLink(${link.id})" ${tooltipAttr}>
    <div class="card-body">
        ${actionBtns}
        <div class="d-flex align-items-center mb-1">
            ${dotHtml}
            ${statusText}
        </div>
        <div class="card-title">${escapeHtml(link.name)}</div>
        <div class="site-meta">
            ${responseTime}
            ${lastChecked}
        </div>
    </div>
</div>`;
}

// ── Navigation ───────────────────────────────────────────────────────────────

async function navigateToLink(linkId) {
    try {
        const data = await api.get(`/api/sites/${linkId}/url`);
        window.open(data.url, '_blank', 'noopener,noreferrer');
    } catch (e) {
        showToast(e.message, 'warning');
    }
}

// ── Link Modal ───────────────────────────────────────────────────────────────

async function openLinkModal(linkId, preGroupId = null) {
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('linkModal'));
    const title = document.getElementById('linkModalTitle');
    const errEl = document.getElementById('link-error');

    errEl.classList.add('d-none');
    errEl.textContent = '';
    document.getElementById('link-id').value = '';
    document.getElementById('link-name').value = '';
    document.getElementById('link-url').value = '';
    document.getElementById('link-description').value = '';
    document.getElementById('link-sort-order').value = '0';
    document.getElementById('link-check-interval').value = '300';
    document.getElementById('link-check-timeout').value = '10';
    document.getElementById('link-is-enabled').checked = true;
    document.getElementById('link-check-enabled').checked = true;
    document.getElementById('link-ssl-verify').checked = true;
    document.getElementById('btn-manual-check').classList.add('d-none');

    // Populate groups dropdown
    const sel = document.getElementById('link-group-id');
    sel.innerHTML = '<option value="">(未分類)</option>' +
        allGroups.map(g => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');

    if (linkId) {
        title.innerHTML = '<i class="bi bi-pencil"></i> リンク編集';
        try {
            const [link, urlData] = await Promise.all([
                api.get(`/api/sites/${linkId}`),
                api.get(`/api/sites/${linkId}/url`),
            ]);
            document.getElementById('link-id').value = link.id;
            document.getElementById('link-name').value = link.name;
            document.getElementById('link-url').value = urlData.url;
            document.getElementById('link-description').value = link.description || '';
            sel.value = link.group_id || '';
            document.getElementById('link-sort-order').value = link.sort_order;
            document.getElementById('link-check-interval').value = link.check_interval_sec;
            document.getElementById('link-check-timeout').value = link.check_timeout_sec;
            document.getElementById('link-is-enabled').checked = link.is_enabled;
            document.getElementById('link-check-enabled').checked = link.check_enabled;
            document.getElementById('link-ssl-verify').checked = link.check_ssl_verify;
            document.getElementById('btn-manual-check').classList.remove('d-none');
        } catch (e) {
            showToast(e.message, 'danger');
            return;
        }
    } else {
        title.innerHTML = '<i class="bi bi-link-45deg"></i> リンク追加';
        if (preGroupId !== null) {
            sel.value = preGroupId;
        }
    }
    modal.show();
}

async function saveLink() {
    const errEl = document.getElementById('link-error');
    errEl.classList.add('d-none');

    const linkId = document.getElementById('link-id').value;
    const payload = {
        name: document.getElementById('link-name').value.trim(),
        url: document.getElementById('link-url').value.trim(),
        description: document.getElementById('link-description').value.trim() || null,
        group_id: document.getElementById('link-group-id').value
            ? parseInt(document.getElementById('link-group-id').value) : null,
        sort_order: parseInt(document.getElementById('link-sort-order').value) || 0,
        check_interval_sec: parseInt(document.getElementById('link-check-interval').value) || 300,
        check_timeout_sec: parseInt(document.getElementById('link-check-timeout').value) || 10,
        is_enabled: document.getElementById('link-is-enabled').checked,
        check_enabled: document.getElementById('link-check-enabled').checked,
        check_ssl_verify: document.getElementById('link-ssl-verify').checked,
    };

    if (!payload.name || !payload.url) {
        errEl.textContent = '名称と URL は必須です。';
        errEl.classList.remove('d-none');
        return;
    }

    try {
        if (linkId) {
            await api.put(`/api/sites/${linkId}`, payload);
        } else {
            await api.post('/api/sites/', payload);
        }
        bootstrap.Modal.getInstance(document.getElementById('linkModal')).hide();
        await loadSites();
        showToast('保存しました', 'success');
    } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('d-none');
    }
}

async function deleteLink(linkId) {
    if (!confirm('このリンクを削除しますか？')) return;
    try {
        await api.del(`/api/sites/${linkId}`);
        await loadSites();
        showToast('削除しました', 'success');
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// ── Manual check ─────────────────────────────────────────────────────────────

async function manualCheck() {
    const linkId = document.getElementById('link-id').value;
    if (!linkId) return;
    const btn = document.getElementById('btn-manual-check');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
        const result = await api.post(`/api/sites/${linkId}/check`, {});
        showToast(`${result.status.toUpperCase()}: ${result.message}`, result.status === 'up' ? 'success' : 'warning');
        await loadSites();
    } catch (e) {
        showToast(e.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 今すぐチェック';
    }
}

// ── Group Modal ───────────────────────────────────────────────────────────────

async function openGroupModal(groupId) {
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('groupModal'));
    const title = document.getElementById('groupModalTitle');
    const errEl = document.getElementById('group-error');

    errEl.classList.add('d-none');
    errEl.textContent = '';

    const deletebtn = document.getElementById('btn-delete-group');
    if (groupId) {
        title.innerHTML = '<i class="bi bi-pencil"></i> グループ編集';
        const group = allGroups.find(g => g.id === groupId);
        if (group) {
            document.getElementById('group-id').value = group.id;
            document.getElementById('group-name').value = group.name;
            document.getElementById('group-description').value = group.description || '';
            document.getElementById('group-color').value = group.color;
            document.getElementById('group-sort-order').value = group.sort_order;
            document.getElementById('group-icon').value = group.icon || '';
        }
        deletebtn.classList.remove('d-none');
    } else {
        title.innerHTML = '<i class="bi bi-folder-plus"></i> グループ追加';
        document.getElementById('group-id').value = '';
        document.getElementById('group-name').value = '';
        document.getElementById('group-description').value = '';
        document.getElementById('group-color').value = '#6c757d';
        document.getElementById('group-sort-order').value = '0';
        document.getElementById('group-icon').value = '';
        deletebtn.classList.add('d-none');
    }
    modal.show();
}

async function deleteGroup() {
    const groupId = document.getElementById('group-id').value;
    if (!groupId) return;
    if (!confirm('このグループを削除しますか？\nグループ内のリンクは未分類になります。')) return;
    try {
        await api.del(`/api/site-groups/${groupId}`);
        bootstrap.Modal.getInstance(document.getElementById('groupModal')).hide();
        await loadSites();
        showToast('グループを削除しました', 'success');
    } catch (e) {
        const errEl = document.getElementById('group-error');
        errEl.textContent = e.message;
        errEl.classList.remove('d-none');
    }
}

async function saveGroup() {
    const errEl = document.getElementById('group-error');
    errEl.classList.add('d-none');

    const groupId = document.getElementById('group-id').value;
    const payload = {
        name: document.getElementById('group-name').value.trim(),
        description: document.getElementById('group-description').value.trim() || null,
        color: document.getElementById('group-color').value,
        sort_order: parseInt(document.getElementById('group-sort-order').value) || 0,
        icon: document.getElementById('group-icon').value.trim() || null,
    };

    if (!payload.name) {
        errEl.textContent = 'グループ名は必須です。';
        errEl.classList.remove('d-none');
        return;
    }

    try {
        if (groupId) {
            await api.put(`/api/site-groups/${groupId}`, payload);
        } else {
            await api.post('/api/site-groups/', payload);
        }
        bootstrap.Modal.getInstance(document.getElementById('groupModal')).hide();
        await loadSites();
        showToast('保存しました', 'success');
    } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('d-none');
    }
}

// ── WebSocket ────────────────────────────────────────────────────────────────

let wsEnabled = true;

function toggleWebSocket() {
    wsEnabled = !wsEnabled;
    if (wsEnabled) {
        connectWebSocket();
    } else {
        if (ws) ws.close();
        const el = document.getElementById('ws-indicator');
        el.textContent = '自動更新 OFF';
        el.className = 'badge bg-secondary';
        el.title = 'クリックで自動更新を再開';
    }
}

function connectWebSocket() {
    if (!wsEnabled) return;
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/sites`);

    ws.onopen = () => {
        const el = document.getElementById('ws-indicator');
        el.textContent = '自動更新 ●';
        el.className = 'badge bg-success';
        el.title = 'クリックで自動更新を停止';
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'status_update') {
                onStatusUpdate(data);
            }
        } catch (e) { /* ignore */ }
    };

    ws.onclose = () => {
        if (!wsEnabled) return;
        const el = document.getElementById('ws-indicator');
        el.textContent = '再接続中...';
        el.className = 'badge bg-warning text-dark';
        el.title = 'クリックで自動更新を停止';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => ws.close();
}

function onStatusUpdate(data) {
    // Update card in-place
    const card = document.getElementById(`card-${data.link_id}`);
    if (card) {
        // Update status class on card
        card.className = card.className.replace(/status-\w+/, `status-${data.status}`);

        // Update dot
        const dot = card.querySelector('.status-dot');
        if (dot) {
            dot.className = `status-dot ${data.status}`;
            dot.title = data.status;
        }

        // Update status text
        const txt = card.querySelector('.status-text');
        if (txt) {
            txt.className = `status-text ${data.status}`;
            txt.textContent = data.status.toUpperCase();
        }

        // Update meta
        const meta = card.querySelector('.site-meta');
        if (meta) {
            const responseTime = (data.status === 'up' && data.response_time_ms !== null)
                ? `<div>${data.response_time_ms}ms</div>` : '';
            const checkedAt = data.checked_at
                ? `<div>${formatRelativeTime(data.checked_at)}</div>`
                : '<div class="fst-italic">未確認</div>';
            meta.innerHTML = responseTime + checkedAt;
        }

        // Update link data in allLinks array
        const idx = allLinks.findIndex(l => l.id === data.link_id);
        if (idx >= 0) {
            allLinks[idx].status = data.status;
            allLinks[idx].response_time_ms = data.response_time_ms;
            allLinks[idx].http_status_code = data.http_status_code;
            allLinks[idx].last_checked_at = data.checked_at;
        }
    }

    // Toast notification for degraded status
    if (data.status === 'down' || data.status === 'error') {
        showToast(`${escapeHtml(data.name)}: ${data.status.toUpperCase()}`, 'danger');
    }
}

// ── Utilities ────────────────────────────────────────────────────────────────

function formatRelativeTime(isoStr) {
    if (!isoStr) return '未確認';
    const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (diff < 60) return '今';
    if (diff < 3600) return `${Math.floor(diff / 60)}分前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
    return `${Math.floor(diff / 86400)}日前`;
}
