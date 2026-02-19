let ws = null;

async function loadPresence() {
    const [myStatus, allStatuses, logs] = await Promise.all([
        api.get('/api/presence/me'),
        api.get('/api/presence/statuses'),
        api.get('/api/presence/logs')
    ]);

    document.getElementById('my-status').value = myStatus.status;
    document.getElementById('my-message').value = myStatus.message || '';

    renderStatuses(allStatuses);
    renderLogs(logs);
}

function renderTickets(tickets) {
    if (!tickets || tickets.length === 0) return '<span class="text-muted">-</span>';
    const space = window.__backlogSpace || 'ottsystems';
    const badges = tickets.map(t =>
        `<a href="https://${escapeHtml(space)}.backlog.com/view/${escapeHtml(t.backlog_ticket_id)}" target="_blank" class="badge bg-info text-decoration-none"><i class="bi bi-link-45deg"></i> ${escapeHtml(t.backlog_ticket_id)}</a>`
    ).join('');
    return `<div class="d-flex flex-wrap gap-1">${badges}</div>`;
}

function renderStatuses(statuses) {
    const tbody = document.getElementById('status-table');
    if (statuses.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-muted">${i18n.t('No users')}</td></tr>`;
        return;
    }
    tbody.innerHTML = statuses.map(s => `
        <tr>
            <td>${escapeHtml(s.display_name)}</td>
            <td><span class="badge presence-${s.status}">${s.status}</span></td>
            <td>${s.message ? escapeHtml(s.message) : '<span class="text-muted">-</span>'}</td>
            <td>${renderTickets(s.active_tickets)}</td>
            <td>${s.updated_at ? new Date(s.updated_at).toLocaleString() : '-'}</td>
        </tr>
    `).join('');
}

function renderLogs(logs) {
    const el = document.getElementById('my-logs');
    if (logs.length === 0) {
        el.innerHTML = `<div class="list-group-item text-muted">${i18n.t('No history')}</div>`;
        return;
    }
    el.innerHTML = logs.slice(0, 10).map(l => `
        <div class="list-group-item d-flex justify-content-between align-items-center py-1">
            <span><span class="badge presence-${l.status}">${l.status}</span>
                ${l.message ? '<small class="text-muted ms-1">' + escapeHtml(l.message) + '</small>' : ''}</span>
            <small class="text-muted">${new Date(l.changed_at).toLocaleString()}</small>
        </div>
    `).join('');
}

async function updateMyStatus() {
    const status = document.getElementById('my-status').value;
    const message = document.getElementById('my-message').value || null;
    await api.put('/api/presence/status', { status, message });
    loadPresence();
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/presence`);

    ws.onopen = () => {
        document.getElementById('ws-badge').textContent = i18n.t('Connected');
        document.getElementById('ws-badge').className = 'badge bg-success ms-2';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'presence_update') {
            loadPresence();
        }
    };

    ws.onclose = () => {
        document.getElementById('ws-badge').textContent = i18n.t('Disconnected');
        document.getElementById('ws-badge').className = 'badge bg-secondary ms-2';
        setTimeout(connectWebSocket, 3000);
    };
}

loadPresence();
connectWebSocket();
