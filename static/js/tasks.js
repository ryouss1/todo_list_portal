let allTasks = [];
let timerIntervals = {};
let categoryMap = {};

async function loadCategories() {
    const cats = await getCategories();
    categoryMap = {};
    const sel = document.getElementById('task-category');
    sel.innerHTML = `<option value="">${i18n.t('-- None --')}</option>`;
    cats.forEach(c => {
        categoryMap[c.id] = c.name;
        sel.innerHTML += `<option value="${c.id}">${escapeHtml(c.name)}</option>`;
    });
}

async function loadTasks() {
    allTasks = await api.get('/api/tasks/');
    renderTasks();
    checkOverdueTasks();
}

function renderTasks() {
    const el = document.getElementById('task-list');
    if (allTasks.length === 0) {
        el.innerHTML = `<div class="col-12 text-muted text-center py-4">${i18n.t('No tasks yet')}</div>`;
        return;
    }
    el.innerHTML = allTasks.map(t => `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title mb-0">${escapeHtml(t.title)}</h6>
                        <div class="d-flex gap-1">
                            ${t.category_id && categoryMap[t.category_id] ? '<span class="badge bg-light text-dark border">' + escapeHtml(categoryMap[t.category_id]) + '</span>' : ''}
                            <span class="badge bg-${statusColor(t.status)}">${t.status}</span>
                        </div>
                    </div>
                    ${t.description ? '<p class="card-text small text-muted">' + escapeHtml(t.description) + '</p>' : ''}
                    ${t.backlog_ticket_id ? '<div class="mb-2"><a href="https://' + escapeHtml(window.__backlogSpace || 'ottsystems') + '.backlog.com/view/' + escapeHtml(t.backlog_ticket_id) + '" target="_blank" class="badge bg-info text-decoration-none"><i class="bi bi-link-45deg"></i> ' + escapeHtml(t.backlog_ticket_id) + '</a></div>' : ''}
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" id="report-${t.id}"
                            ${t.report ? 'checked' : ''} onchange="toggleReport(${t.id}, this.checked)">
                        <label class="form-check-label small" for="report-${t.id}">${i18n.t('Report')}</label>
                    </div>
                    <div class="timer-display text-center my-3" id="timer-${t.id}">
                        ${formatTime(t.total_seconds)}
                    </div>
                    <div class="d-flex justify-content-center gap-2">
                        <button class="btn btn-success btn-sm" id="btn-start-${t.id}" onclick="startTimer(${t.id})">
                            <i class="bi bi-play-fill"></i> ${i18n.t('Start')}
                        </button>
                        <button class="btn btn-warning btn-sm" id="btn-stop-${t.id}" onclick="stopTimer(${t.id})" disabled>
                            <i class="bi bi-stop-fill"></i> ${i18n.t('Stop')}
                        </button>
                        <button class="btn btn-info btn-sm" onclick="doneTask(${t.id})">
                            <i class="bi bi-check-lg"></i> ${i18n.t('Done')}
                        </button>
                    </div>
                </div>
                <div class="card-footer d-flex justify-content-between">
                    <button class="btn btn-outline-primary btn-sm" onclick="openEditTask(${t.id})">
                        <i class="bi bi-pencil"></i> ${i18n.t('Edit')}
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteTask(${t.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    // Check for active timers
    allTasks.forEach(t => checkActiveTimer(t));
}

async function checkActiveTimer(task) {
    const entries = await api.get(`/api/tasks/${task.id}/time-entries`);
    const active = entries.find(e => !e.stopped_at);
    if (active) {
        enableStopButton(task.id, new Date(active.started_at), task.total_seconds);
    }
}

function enableStopButton(taskId, startedAt, baseTotalSeconds) {
    const btnStart = document.getElementById(`btn-start-${taskId}`);
    const btnStop = document.getElementById(`btn-stop-${taskId}`);
    if (btnStart) btnStart.disabled = true;
    if (btnStop) btnStop.disabled = false;

    if (timerIntervals[taskId]) clearInterval(timerIntervals[taskId]);
    timerIntervals[taskId] = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startedAt.getTime()) / 1000);
        const timerEl = document.getElementById(`timer-${taskId}`);
        if (timerEl) timerEl.textContent = formatTime(baseTotalSeconds + elapsed);
    }, 1000);
}

async function startTimer(taskId) {
    try {
        await api.post(`/api/tasks/${taskId}/start`);
        loadTasks();
    } catch (e) {
        console.error(e.message);
    }
}

async function stopTimer(taskId) {
    await api.post(`/api/tasks/${taskId}/stop`);
    if (timerIntervals[taskId]) { clearInterval(timerIntervals[taskId]); delete timerIntervals[taskId]; }
    loadTasks();
}

async function toggleReport(taskId, checked) {
    await api.put(`/api/tasks/${taskId}`, { report: checked });
}

async function doneTask(taskId) {
    if (!confirm(i18n.t('Complete this task?'))) return;
    await api.post(`/api/tasks/${taskId}/done`);
    if (timerIntervals[taskId]) { clearInterval(timerIntervals[taskId]); delete timerIntervals[taskId]; }
    loadTasks();
}

function openNewTask() {
    document.getElementById('taskModalTitle').textContent = i18n.t('New Task');
    document.getElementById('task-id').value = '';
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-category').value = '';
    document.getElementById('task-backlog-ticket').value = '';
}

function openEditTask(id) {
    const t = allTasks.find(x => x.id === id);
    if (!t) return;
    document.getElementById('taskModalTitle').textContent = i18n.t('Edit Task');
    document.getElementById('task-id').value = t.id;
    document.getElementById('task-title').value = t.title;
    document.getElementById('task-description').value = t.description || '';
    document.getElementById('task-category').value = t.category_id || '';
    document.getElementById('task-backlog-ticket').value = t.backlog_ticket_id || '';
    new bootstrap.Modal(document.getElementById('taskModal')).show();
}

async function saveTask() {
    const id = document.getElementById('task-id').value;
    const catVal = document.getElementById('task-category').value;
    const data = {
        title: document.getElementById('task-title').value,
        description: document.getElementById('task-description').value || null,
        category_id: catVal ? parseInt(catVal) : null,
        backlog_ticket_id: document.getElementById('task-backlog-ticket').value || null,
    };
    if (!data.title) return alert(i18n.t('Title is required'));

    if (id) {
        await api.put(`/api/tasks/${id}`, data);
    } else {
        await api.post('/api/tasks/', data);
    }
    bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
    loadTasks();
}

async function deleteTask(id) {
    if (!confirm(i18n.t('Delete this task?'))) return;
    await api.del(`/api/tasks/${id}`);
    if (timerIntervals[id]) { clearInterval(timerIntervals[id]); delete timerIntervals[id]; }
    loadTasks();
}

function statusColor(s) {
    switch(s) {
        case 'in_progress': return 'primary';
        default: return 'secondary';
    }
}

function checkOverdueTasks() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const overdue = allTasks.filter(t => {
        const d = new Date(t.updated_at || t.created_at);
        d.setHours(0, 0, 0, 0);
        return d < today;
    });
    if (overdue.length === 0) return;

    const listEl = document.getElementById('overdue-list');
    listEl.innerHTML = overdue.map(t => {
        const d = new Date(t.updated_at || t.created_at);
        const dateStr = d.toLocaleDateString();
        return `
            <div class="mb-3 border rounded p-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong>${escapeHtml(t.title)}</strong>
                    <small class="text-muted">${dateStr}</small>
                </div>
                <label class="form-label small mb-1">${i18n.t('End time:')}</label>
                <input type="time" class="form-control form-control-sm overdue-time" data-task-id="${t.id}" value="18:00">
            </div>
        `;
    }).join('');

    new bootstrap.Modal(document.getElementById('overdueModal')).show();
}

async function submitOverdue() {
    const inputs = document.querySelectorAll('.overdue-time');
    const tasks = [];
    inputs.forEach(inp => {
        tasks.push({ task_id: parseInt(inp.dataset.taskId), end_time: inp.value });
    });
    await api.post('/api/tasks/batch-done', { tasks });
    bootstrap.Modal.getInstance(document.getElementById('overdueModal')).hide();
    loadTasks();
}

loadCategories().then(() => loadTasks());
