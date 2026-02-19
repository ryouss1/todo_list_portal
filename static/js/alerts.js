let allAlerts = [];
let alertFilter = 'all';
let severityFilter = 'all';
let sourceFilter = '';
let keywordFilter = '';
let keywordTimeout = null;
let alertWs = null;

// --- Alerts ---

async function loadAlerts() {
    const params = alertFilter === 'active' ? '?active_only=true' : '';
    allAlerts = await api.get(`/api/alerts/${params}`);
    updateSourceDropdown();
    renderAlerts();
}

function getFilteredAlerts() {
    return allAlerts.filter(a => {
        if (severityFilter !== 'all' && a.severity !== severityFilter) return false;
        if (sourceFilter && (a.source || '') !== sourceFilter) return false;
        if (keywordFilter) {
            const kw = keywordFilter.toLowerCase();
            const titleMatch = (a.title || '').toLowerCase().includes(kw);
            const msgMatch = (a.message || '').toLowerCase().includes(kw);
            if (!titleMatch && !msgMatch) return false;
        }
        return true;
    });
}

function updateSourceDropdown() {
    const select = document.getElementById('alert-source-filter');
    const current = select.value;
    const sources = [...new Set(allAlerts.map(a => a.source).filter(Boolean))].sort();
    select.innerHTML = `<option value="">${i18n.t('All Sources')}</option>` +
        sources.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
    if (sources.includes(current)) {
        select.value = current;
    } else {
        select.value = '';
        sourceFilter = '';
    }
}

function truncateMessage(msg, maxLen) {
    if (!msg) return '';
    var firstLine = msg.split('\n')[0];
    if (firstLine.length > maxLen) return firstLine.substring(0, maxLen) + '...';
    if (msg.includes('\n')) return firstLine + '...';
    return firstLine;
}

function renderAlerts() {
    const container = document.getElementById('alert-list');
    const filtered = getFilteredAlerts();
    if (filtered.length === 0) {
        container.innerHTML = `<div class="text-muted text-center py-4">${allAlerts.length > 0 ? i18n.t('No matching alerts') : i18n.t('No alerts')}</div>`;
        return;
    }
    container.innerHTML = filtered.map(a => {
        var hasDetail = a.message && (a.message.length > 80 || a.message.includes('\n'));
        var preview = truncateMessage(a.message, 80);
        return `
        <div class="card mb-2 border-${alertSeverityColor(a.severity)} ${!a.is_active ? 'opacity-50' : ''}">
            <div class="card-body py-2 px-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="alert-header-clickable" role="button" data-alert-id="${a.id}" style="cursor:pointer;flex:1">
                        <span class="badge bg-${alertSeverityColor(a.severity)} me-2">${escapeHtml(a.severity)}</span>
                        <strong>${escapeHtml(a.title)}</strong>
                        ${a.source ? '<small class="text-muted ms-2">[' + escapeHtml(a.source) + ']</small>' : ''}
                        ${a.rule_id ? `<span class="badge bg-secondary ms-1">${i18n.t('auto')}</span>` : ''}
                        ${hasDetail ? '<i class="bi bi-chevron-down ms-2 text-muted small alert-chevron"></i>' : ''}
                    </div>
                    <div>
                        ${a.acknowledged
                            ? `<span class="badge bg-success">${i18n.t('Acknowledged')}</span>`
                            : a.is_active
                                ? `<button class="btn btn-outline-success btn-sm me-1" onclick="acknowledgeAlert(${a.id})">
                                     <i class="bi bi-check-lg"></i> ${i18n.t('Acknowledge')}
                                   </button>`
                                : ''}
                        ${a.is_active
                            ? `<button class="btn btn-outline-secondary btn-sm" onclick="deactivateAlert(${a.id})">
                                 <i class="bi bi-x-lg"></i>
                               </button>`
                            : `<span class="badge bg-secondary">${i18n.t('Inactive')}</span>`}
                    </div>
                </div>
                <div class="mt-1 alert-preview" data-alert-id="${a.id}">
                    <small class="text-muted">${escapeHtml(preview)}</small>
                </div>
                <div class="mt-1 alert-detail d-none" data-alert-id="${a.id}">
                    <small style="white-space:pre-wrap">${escapeHtml(a.message)}</small>
                </div>
                <div class="mt-1">
                    <small class="text-muted">${new Date(a.created_at).toLocaleString()}</small>
                </div>
            </div>
        </div>`;
    }).join('');
}

function filterAlerts(filter, btn) {
    alertFilter = filter;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadAlerts();
}

function setSeverityFilter(severity, btn) {
    severityFilter = severity;
    document.querySelectorAll('#alert-filter-bar .btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderAlerts();
}

function setSourceFilter(value) {
    sourceFilter = value;
    renderAlerts();
}

async function createAlert() {
    const data = {
        title: document.getElementById('alert-title').value,
        message: document.getElementById('alert-message').value,
        severity: document.getElementById('alert-severity').value,
        source: document.getElementById('alert-source').value || null,
    };
    await api.post('/api/alerts/', data);
    showToast(i18n.t('Alert created'));
    bootstrap.Modal.getInstance(document.getElementById('alertModal')).hide();
    document.getElementById('alert-title').value = '';
    document.getElementById('alert-message').value = '';
    document.getElementById('alert-source').value = '';
    loadAlerts();
}

async function acknowledgeAlert(id) {
    await api.patch(`/api/alerts/${id}/acknowledge`);
    showToast(i18n.t('Alert acknowledged'));
    loadAlerts();
}

async function deactivateAlert(id) {
    await api.patch(`/api/alerts/${id}/deactivate`);
    showToast(i18n.t('Alert deactivated'));
    loadAlerts();
}

function alertSeverityColor(s) {
    switch(s) {
        case 'critical': return 'danger';
        case 'warning': return 'warning';
        default: return 'info';
    }
}

// --- Alert Rules ---

async function loadRules() {
    const rules = await api.get('/api/alert-rules/');
    renderRules(rules);
}

function renderRules(rules) {
    const tbody = document.getElementById('rule-list');
    if (rules.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-muted text-center">${i18n.t('No alert rules configured')}</td></tr>`;
        return;
    }
    tbody.innerHTML = rules.map(r => `
        <tr>
            <td>${escapeHtml(r.name)}</td>
            <td><code>${escapeHtml(JSON.stringify(r.condition))}</code></td>
            <td><span class="badge bg-${alertSeverityColor(r.severity)}">${escapeHtml(r.severity)}</span></td>
            <td>
                ${r.is_enabled
                    ? `<span class="badge bg-success">${i18n.t('Enabled')}</span>`
                    : `<span class="badge bg-secondary">${i18n.t('Disabled')}</span>`}
            </td>
            <td>
                <button class="btn btn-outline-primary btn-sm me-1" onclick="editRule(${r.id})" title="${i18n.t('Edit')}">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-${r.is_enabled ? 'warning' : 'success'} btn-sm me-1"
                        onclick="toggleRule(${r.id}, ${!r.is_enabled})" title="${r.is_enabled ? i18n.t('Disable') : i18n.t('Enable')}">
                    <i class="bi bi-${r.is_enabled ? 'pause' : 'play'}"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteRule(${r.id})" title="${i18n.t('Delete')}">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function openRuleModal(rule) {
    document.getElementById('ruleModalTitle').textContent = rule ? i18n.t('Edit Alert Rule') : i18n.t('Add Alert Rule');
    document.getElementById('rule-id').value = rule ? rule.id : '';
    document.getElementById('rule-name').value = rule ? rule.name : '';
    document.getElementById('rule-severity').value = rule ? rule.severity : 'warning';
    document.getElementById('rule-condition').value = rule ? JSON.stringify(rule.condition, null, 2) : '';
    document.getElementById('rule-title-template').value = rule ? rule.alert_title_template : '';
    document.getElementById('rule-message-template').value = rule ? (rule.alert_message_template || '') : '';
    document.getElementById('rule-is-enabled').checked = rule ? rule.is_enabled : true;
    // Reset to Basic tab
    const firstTab = document.querySelector('#ruleModal .stl-tabs .nav-link');
    if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
}

async function editRule(id) {
    const rule = await api.get(`/api/alert-rules/${id}`);
    openRuleModal(rule);
    new bootstrap.Modal(document.getElementById('ruleModal')).show();
}

async function saveRule() {
    const id = document.getElementById('rule-id').value;
    let condition;
    try {
        condition = JSON.parse(document.getElementById('rule-condition').value);
    } catch(e) {
        showToast(i18n.t('Invalid JSON in condition'));
        return;
    }
    const data = {
        name: document.getElementById('rule-name').value,
        condition: condition,
        alert_title_template: document.getElementById('rule-title-template').value,
        alert_message_template: document.getElementById('rule-message-template').value || null,
        severity: document.getElementById('rule-severity').value,
        is_enabled: document.getElementById('rule-is-enabled').checked,
    };

    if (id) {
        await api.put(`/api/alert-rules/${id}`, data);
        showToast(i18n.t('Alert rule updated'));
    } else {
        await api.post('/api/alert-rules/', data);
        showToast(i18n.t('Alert rule created'));
    }

    bootstrap.Modal.getInstance(document.getElementById('ruleModal')).hide();
    loadRules();
}

async function toggleRule(id, enabled) {
    await api.put(`/api/alert-rules/${id}`, { is_enabled: enabled });
    showToast(enabled ? i18n.t('Rule enabled') : i18n.t('Rule disabled'));
    loadRules();
}

async function deleteRule(id) {
    if (!confirm(i18n.t('Delete this alert rule?'))) return;
    await api.del(`/api/alert-rules/${id}`);
    showToast(i18n.t('Alert rule deleted'));
    loadRules();
}

// --- WebSocket ---

function connectAlertWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    alertWs = new WebSocket(`${protocol}//${location.host}/ws/alerts`);
    const statusEl = document.getElementById('alert-ws-status');

    alertWs.onopen = () => {
        statusEl.textContent = i18n.t('Connected');
        statusEl.className = 'badge bg-success me-2';
    };

    alertWs.onclose = () => {
        statusEl.textContent = i18n.t('Disconnected');
        statusEl.className = 'badge bg-danger me-2';
        setTimeout(connectAlertWebSocket, 3000);
    };

    alertWs.onerror = () => {
        alertWs.close();
    };

    alertWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_alert') {
            allAlerts.unshift(data.alert);
            updateSourceDropdown();
            renderAlerts();
        }
    };
}

// --- Alert expand/collapse ---

document.addEventListener('click', function(e) {
    var header = e.target.closest('.alert-header-clickable');
    if (!header) return;
    // Don't toggle if clicking a button inside
    if (e.target.closest('button')) return;
    var alertId = header.getAttribute('data-alert-id');
    var preview = document.querySelector('.alert-preview[data-alert-id="' + alertId + '"]');
    var detail = document.querySelector('.alert-detail[data-alert-id="' + alertId + '"]');
    var chevron = header.querySelector('.alert-chevron');
    if (!detail) return;

    var isExpanded = !detail.classList.contains('d-none');
    if (isExpanded) {
        detail.classList.add('d-none');
        if (preview) preview.classList.remove('d-none');
        if (chevron) {
            chevron.classList.remove('bi-chevron-up');
            chevron.classList.add('bi-chevron-down');
        }
    } else {
        detail.classList.remove('d-none');
        if (preview) preview.classList.add('d-none');
        if (chevron) {
            chevron.classList.remove('bi-chevron-down');
            chevron.classList.add('bi-chevron-up');
        }
    }
});

// --- Init ---

// Keyword search with debounce
document.getElementById('alert-keyword-filter').addEventListener('input', function() {
    clearTimeout(keywordTimeout);
    keywordTimeout = setTimeout(() => {
        keywordFilter = this.value.trim();
        renderAlerts();
    }, 300);
});

loadAlerts();
loadRules();
connectAlertWebSocket();
