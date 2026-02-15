let report = null;
let currentUserId = null;
let allUsers = {};
let allCategories = [];
let categoryMap = {};

function formatMinutes(m) {
    if (!m) return '0m';
    const h = Math.floor(m / 60);
    const min = m % 60;
    if (h > 0 && min > 0) return `${h}h ${min}m`;
    if (h > 0) return `${h}h`;
    return `${min}m`;
}

async function loadReport() {
    const [r, me, users, categories] = await Promise.all([
        api.get(`/api/reports/${REPORT_ID}`),
        api.get('/api/auth/me'),
        api.get('/api/users/'),
        api.get('/api/task-categories/')
    ]);
    report = r;
    currentUserId = me.user_id;
    users.forEach(u => { allUsers[u.id] = u.display_name; });
    allCategories = categories;
    categories.forEach(c => { categoryMap[c.id] = c.name; });

    renderReport();
}

function renderReport() {
    const el = document.getElementById('report-content');

    const sections = [];
    if (report.achievements) {
        sections.push(`
            <div class="card border-success mb-3">
                <div class="card-header bg-success bg-opacity-10 text-success"><i class="bi bi-trophy"></i> Achievements</div>
                <div class="card-body">${escapeHtml(report.achievements).replace(/\n/g, '<br>')}</div>
            </div>`);
    }
    if (report.issues) {
        sections.push(`
            <div class="card border-danger mb-3">
                <div class="card-header bg-danger bg-opacity-10 text-danger"><i class="bi bi-exclamation-triangle"></i> Issues</div>
                <div class="card-body">${escapeHtml(report.issues).replace(/\n/g, '<br>')}</div>
            </div>`);
    }
    if (report.next_plan) {
        sections.push(`
            <div class="card border-primary mb-3">
                <div class="card-header bg-primary bg-opacity-10 text-primary"><i class="bi bi-arrow-right-circle"></i> Next Plan</div>
                <div class="card-body">${escapeHtml(report.next_plan).replace(/\n/g, '<br>')}</div>
            </div>`);
    }
    if (report.remarks) {
        sections.push(`
            <div class="card border-secondary mb-3">
                <div class="card-header bg-secondary bg-opacity-10 text-secondary"><i class="bi bi-chat-dots"></i> Remarks</div>
                <div class="card-body">${escapeHtml(report.remarks).replace(/\n/g, '<br>')}</div>
            </div>`);
    }

    el.innerHTML = `
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><strong>${report.report_date}</strong>
                    <span class="text-muted ms-2">by ${escapeHtml(allUsers[report.user_id] || 'Unknown')}</span>
                </span>
                <small class="text-muted">Created: ${new Date(report.created_at).toLocaleString()}</small>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-md-4">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <i class="bi bi-tag text-info"></i>
                            <span class="text-muted small">タスク分類</span>
                        </div>
                        <span class="badge bg-info text-dark fs-6">${escapeHtml(categoryMap[report.category_id] || '-')}</span>
                    </div>
                    <div class="col-md-4">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <i class="bi bi-card-text text-primary"></i>
                            <span class="text-muted small">タスク名</span>
                        </div>
                        <span class="fw-semibold">${escapeHtml(report.task_name || '')}</span>
                    </div>
                    <div class="col-md-4">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <i class="bi bi-clock text-warning"></i>
                            <span class="text-muted small">時間</span>
                        </div>
                        <span class="badge bg-warning text-dark fs-6">${formatMinutes(report.time_minutes)}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="card border-dark mb-3">
            <div class="card-header bg-dark bg-opacity-10"><i class="bi bi-pencil-square"></i> Work Content</div>
            <div class="card-body">${escapeHtml(report.work_content).replace(/\n/g, '<br>')}</div>
        </div>

        ${sections.join('')}
    `;

    const ownerActions = document.getElementById('owner-actions');
    if (report.user_id === currentUserId) {
        ownerActions.innerHTML = `
            <button class="btn btn-outline-primary btn-sm" onclick="openEdit()">
                <i class="bi bi-pencil"></i> Edit
            </button>
            <button class="btn btn-outline-danger btn-sm" onclick="deleteReport()">
                <i class="bi bi-trash"></i> Delete
            </button>
        `;
    }
}

function populateCategorySelect(selectId, selectedId) {
    const sel = document.getElementById(selectId);
    sel.innerHTML = '<option value="">-- 選択 --</option>' +
        allCategories.map(c => `<option value="${c.id}" ${c.id === selectedId ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
}

function openEdit() {
    populateCategorySelect('edit-category', report.category_id);
    document.getElementById('edit-task-name').value = report.task_name || '';
    document.getElementById('edit-time-minutes').value = report.time_minutes || 0;
    document.getElementById('edit-work-content').value = report.work_content;
    document.getElementById('edit-achievements').value = report.achievements || '';
    document.getElementById('edit-issues').value = report.issues || '';
    document.getElementById('edit-next-plan').value = report.next_plan || '';
    document.getElementById('edit-remarks').value = report.remarks || '';
    new bootstrap.Modal(document.getElementById('editReportModal')).show();
}

async function saveEdit() {
    const categoryId = parseInt(document.getElementById('edit-category').value);
    const taskName = document.getElementById('edit-task-name').value;
    const data = {
        category_id: categoryId,
        task_name: taskName,
        time_minutes: parseInt(document.getElementById('edit-time-minutes').value) || 0,
        work_content: document.getElementById('edit-work-content').value,
        achievements: document.getElementById('edit-achievements').value || null,
        issues: document.getElementById('edit-issues').value || null,
        next_plan: document.getElementById('edit-next-plan').value || null,
        remarks: document.getElementById('edit-remarks').value || null,
    };
    if (!data.work_content) return alert('Work content is required');
    if (!categoryId) return alert('タスク分類 is required');
    if (!taskName) return alert('タスク名 is required');

    await api.put(`/api/reports/${REPORT_ID}`, data);
    bootstrap.Modal.getInstance(document.getElementById('editReportModal')).hide();
    loadReport();
}

async function deleteReport() {
    if (!confirm('Delete this report?')) return;
    await api.del(`/api/reports/${REPORT_ID}`);
    window.location.href = '/reports';
}

loadReport();
