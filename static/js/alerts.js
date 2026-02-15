let allAlerts = [];
let alertFilter = 'all';
let alertWs = null;

// --- Alerts ---

async function loadAlerts() {
    const params = alertFilter === 'active' ? '?active_only=true' : '';
    allAlerts = await api.get(`/api/alerts/${params}`);
    renderAlerts();
}

function renderAlerts() {
    const container = document.getElementById('alert-list');
    if (allAlerts.length === 0) {
        container.innerHTML = '<div class="text-muted text-center py-4">No alerts</div>';
        return;
    }
    container.innerHTML = allAlerts.map(a => `
        <div class="card mb-2 border-${alertSeverityColor(a.severity)} ${!a.is_active ? 'opacity-50' : ''}">
            <div class="card-body py-2 px-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span class="badge bg-${alertSeverityColor(a.severity)} me-2">${escapeHtml(a.severity)}</span>
                        <strong>${escapeHtml(a.title)}</strong>
                        ${a.source ? '<small class="text-muted ms-2">[' + escapeHtml(a.source) + ']</small>' : ''}
                        ${a.rule_id ? '<span class="badge bg-secondary ms-1">auto</span>' : ''}
                    </div>
                    <div>
                        ${a.acknowledged
                            ? '<span class="badge bg-success">Acknowledged</span>'
                            : a.is_active
                                ? `<button class="btn btn-outline-success btn-sm me-1" onclick="acknowledgeAlert(${a.id})">
                                     <i class="bi bi-check-lg"></i> Acknowledge
                                   </button>`
                                : ''}
                        ${a.is_active
                            ? `<button class="btn btn-outline-secondary btn-sm" onclick="deactivateAlert(${a.id})">
                                 <i class="bi bi-x-lg"></i>
                               </button>`
                            : '<span class="badge bg-secondary">Inactive</span>'}
                    </div>
                </div>
                <div class="mt-1">
                    <small>${escapeHtml(a.message)}</small>
                </div>
                <div class="mt-1">
                    <small class="text-muted">${new Date(a.created_at).toLocaleString()}</small>
                </div>
            </div>
        </div>
    `).join('');
}

function filterAlerts(filter, btn) {
    alertFilter = filter;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadAlerts();
}

async function createAlert() {
    const data = {
        title: document.getElementById('alert-title').value,
        message: document.getElementById('alert-message').value,
        severity: document.getElementById('alert-severity').value,
        source: document.getElementById('alert-source').value || null,
    };
    await api.post('/api/alerts/', data);
    showToast('Alert created');
    bootstrap.Modal.getInstance(document.getElementById('alertModal')).hide();
    document.getElementById('alert-title').value = '';
    document.getElementById('alert-message').value = '';
    document.getElementById('alert-source').value = '';
    loadAlerts();
}

async function acknowledgeAlert(id) {
    await api.patch(`/api/alerts/${id}/acknowledge`);
    showToast('Alert acknowledged');
    loadAlerts();
}

async function deactivateAlert(id) {
    await api.patch(`/api/alerts/${id}/deactivate`);
    showToast('Alert deactivated');
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
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No alert rules configured</td></tr>';
        return;
    }
    tbody.innerHTML = rules.map(r => `
        <tr>
            <td>${escapeHtml(r.name)}</td>
            <td><code>${escapeHtml(JSON.stringify(r.condition))}</code></td>
            <td><span class="badge bg-${alertSeverityColor(r.severity)}">${escapeHtml(r.severity)}</span></td>
            <td>
                ${r.is_enabled
                    ? '<span class="badge bg-success">Enabled</span>'
                    : '<span class="badge bg-secondary">Disabled</span>'}
            </td>
            <td>
                <button class="btn btn-outline-primary btn-sm me-1" onclick="editRule(${r.id})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-${r.is_enabled ? 'warning' : 'success'} btn-sm me-1"
                        onclick="toggleRule(${r.id}, ${!r.is_enabled})" title="${r.is_enabled ? 'Disable' : 'Enable'}">
                    <i class="bi bi-${r.is_enabled ? 'pause' : 'play'}"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteRule(${r.id})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function openRuleModal(rule) {
    document.getElementById('ruleModalTitle').textContent = rule ? 'Edit Alert Rule' : 'Add Alert Rule';
    document.getElementById('rule-id').value = rule ? rule.id : '';
    document.getElementById('rule-name').value = rule ? rule.name : '';
    document.getElementById('rule-severity').value = rule ? rule.severity : 'warning';
    document.getElementById('rule-condition').value = rule ? JSON.stringify(rule.condition, null, 2) : '';
    document.getElementById('rule-title-template').value = rule ? rule.alert_title_template : '';
    document.getElementById('rule-message-template').value = rule ? (rule.alert_message_template || '') : '';
    document.getElementById('rule-is-enabled').checked = rule ? rule.is_enabled : true;
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
        showToast('Invalid JSON in condition');
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
        showToast('Alert rule updated');
    } else {
        await api.post('/api/alert-rules/', data);
        showToast('Alert rule created');
    }

    bootstrap.Modal.getInstance(document.getElementById('ruleModal')).hide();
    loadRules();
}

async function toggleRule(id, enabled) {
    await api.put(`/api/alert-rules/${id}`, { is_enabled: enabled });
    showToast(enabled ? 'Rule enabled' : 'Rule disabled');
    loadRules();
}

async function deleteRule(id) {
    if (!confirm('Delete this alert rule?')) return;
    await api.del(`/api/alert-rules/${id}`);
    showToast('Alert rule deleted');
    loadRules();
}

// --- WebSocket ---

function connectAlertWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    alertWs = new WebSocket(`${protocol}//${location.host}/ws/alerts`);
    const statusEl = document.getElementById('alert-ws-status');

    alertWs.onopen = () => {
        statusEl.textContent = 'Connected';
        statusEl.className = 'badge bg-success me-2';
    };

    alertWs.onclose = () => {
        statusEl.textContent = 'Disconnected';
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
            renderAlerts();
        }
    };
}

// --- Init ---

loadAlerts();
loadRules();
connectAlertWebSocket();
