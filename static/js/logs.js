let allLogs = [];
let currentFilter = 'all';
let ws = null;

// --- Logs ---

async function loadLogs() {
    allLogs = await api.get('/api/logs/?limit=100');
    renderLogs();
}

function renderLogs() {
    let filtered = allLogs;
    if (currentFilter === 'important') {
        filtered = allLogs.filter(l => ['WARNING', 'ERROR', 'CRITICAL'].includes(l.severity));
    }

    const tbody = document.getElementById('log-list');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No logs</td></tr>';
        return;
    }
    tbody.innerHTML = filtered.map(l => `
        <tr class="log-row-${l.severity}">
            <td><small>${new Date(l.received_at).toLocaleString()}</small></td>
            <td><span class="badge bg-${severityColor(l.severity)}">${l.severity}</span></td>
            <td><small>${escapeHtml(l.system_name)}</small></td>
            <td><small>${escapeHtml(l.log_type)}</small></td>
            <td>${escapeHtml(l.message)}</td>
        </tr>
    `).join('');
}

function filterLogs(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderLogs();
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/logs`);
    const statusEl = document.getElementById('ws-status');

    ws.onopen = () => {
        statusEl.textContent = 'Connected';
        statusEl.className = 'badge bg-success me-2';
    };

    ws.onclose = () => {
        statusEl.textContent = 'Disconnected';
        statusEl.className = 'badge bg-danger me-2';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };

    ws.onmessage = (event) => {
        const log = JSON.parse(event.data);
        allLogs.unshift(log);
        if (allLogs.length > 200) allLogs.pop();
        renderLogs();
    };
}

function severityColor(s) {
    switch(s) {
        case 'ERROR': case 'CRITICAL': return 'danger';
        case 'WARNING': return 'warning';
        case 'DEBUG': return 'secondary';
        default: return 'info';
    }
}

// --- Log Sources ---

async function loadSources() {
    const sources = await api.get('/api/log-sources/');
    renderSources(sources);
}

function renderSources(sources) {
    const tbody = document.getElementById('source-list');
    if (sources.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No log sources configured</td></tr>';
        return;
    }
    tbody.innerHTML = sources.map(s => `
        <tr>
            <td>${escapeHtml(s.name)}</td>
            <td><small class="font-monospace">${escapeHtml(s.file_path)}</small></td>
            <td>${escapeHtml(s.system_name)}</td>
            <td>${s.polling_interval_sec}s</td>
            <td>
                ${s.is_enabled
                    ? '<span class="badge bg-success">Enabled</span>'
                    : '<span class="badge bg-secondary">Disabled</span>'}
                ${s.last_error
                    ? '<span class="badge bg-danger ms-1" title="' + escapeHtml(s.last_error) + '">Error</span>'
                    : ''}
            </td>
            <td><small>${s.last_collected_at ? new Date(s.last_collected_at).toLocaleString() : 'Never'}</small></td>
            <td>
                <button class="btn btn-outline-primary btn-sm me-1" onclick="editSource(${s.id})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-${s.is_enabled ? 'warning' : 'success'} btn-sm me-1"
                        onclick="toggleSource(${s.id}, ${!s.is_enabled})" title="${s.is_enabled ? 'Disable' : 'Enable'}">
                    <i class="bi bi-${s.is_enabled ? 'pause' : 'play'}"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteSource(${s.id})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function openSourceModal(source) {
    document.getElementById('sourceModalTitle').textContent = source ? 'Edit Log Source' : 'Add Log Source';
    document.getElementById('source-id').value = source ? source.id : '';
    document.getElementById('source-name').value = source ? source.name : '';
    document.getElementById('source-file-path').value = source ? source.file_path : '';
    document.getElementById('source-system-name').value = source ? source.system_name : '';
    document.getElementById('source-log-type').value = source ? source.log_type : '';
    document.getElementById('source-parser-pattern').value = source ? (source.parser_pattern || '') : '';
    document.getElementById('source-severity-field').value = source ? (source.severity_field || '') : '';
    document.getElementById('source-default-severity').value = source ? source.default_severity : 'INFO';
    document.getElementById('source-polling-interval').value = source ? source.polling_interval_sec : 30;
    document.getElementById('source-is-enabled').checked = source ? source.is_enabled : true;
}

async function editSource(id) {
    const source = await api.get(`/api/log-sources/${id}`);
    openSourceModal(source);
    new bootstrap.Modal(document.getElementById('sourceModal')).show();
}

async function saveSource() {
    const id = document.getElementById('source-id').value;
    const data = {
        name: document.getElementById('source-name').value,
        file_path: document.getElementById('source-file-path').value,
        system_name: document.getElementById('source-system-name').value,
        log_type: document.getElementById('source-log-type').value,
        parser_pattern: document.getElementById('source-parser-pattern').value || null,
        severity_field: document.getElementById('source-severity-field').value || null,
        default_severity: document.getElementById('source-default-severity').value,
        polling_interval_sec: parseInt(document.getElementById('source-polling-interval').value),
        is_enabled: document.getElementById('source-is-enabled').checked,
    };

    if (id) {
        await api.put(`/api/log-sources/${id}`, data);
        showToast('Log source updated');
    } else {
        await api.post('/api/log-sources/', data);
        showToast('Log source created');
    }

    bootstrap.Modal.getInstance(document.getElementById('sourceModal')).hide();
    loadSources();
}

async function toggleSource(id, enabled) {
    await api.put(`/api/log-sources/${id}`, { is_enabled: enabled });
    showToast(enabled ? 'Source enabled' : 'Source disabled');
    loadSources();
}

async function deleteSource(id) {
    if (!confirm('Delete this log source?')) return;
    await api.del(`/api/log-sources/${id}`);
    showToast('Log source deleted');
    loadSources();
}

// --- Init ---

loadLogs();
loadSources();
connectWebSocket();
