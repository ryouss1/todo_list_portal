let currentTab = 'my';
let allUsers = {};
let allCategories = [];
let categoryMap = {};

function todayStr() {
    return new Date().toISOString().split('T')[0];
}

async function loadCategories() {
    allCategories = await api.get('/api/task-categories/');
    allCategories.forEach(c => { categoryMap[c.id] = c.name; });
}

async function loadUsers() {
    const users = await api.get('/api/users/');
    users.forEach(u => { allUsers[u.id] = u.display_name; });
}

function formatMinutes(m) {
    if (!m) return '0m';
    const h = Math.floor(m / 60);
    const min = m % 60;
    if (h > 0 && min > 0) return `${h}h ${min}m`;
    if (h > 0) return `${h}h`;
    return `${min}m`;
}

async function loadReports() {
    await Promise.all([loadUsers(), loadCategories()]);
    const filterDate = document.getElementById('filter-date').value || todayStr();
    // Ensure filter input shows the applied date
    document.getElementById('filter-date').value = filterDate;

    let url;
    if (currentTab === 'my') {
        url = `/api/reports/?report_date=${filterDate}`;
    } else {
        url = `/api/reports/all?report_date=${filterDate}`;
    }

    const reports = await api.get(url);
    renderReports(reports);
}

function renderReports(reports) {
    const emptyEl = document.getElementById('report-list');
    const table = document.getElementById('report-table');
    const tbody = document.getElementById('report-tbody');
    const thAuthor = document.getElementById('th-author');

    if (reports.length === 0) {
        table.style.display = 'none';
        emptyEl.innerHTML = '<div class="text-muted text-center py-4">No reports found</div>';
        return;
    }

    emptyEl.innerHTML = '';
    table.style.display = '';
    thAuthor.style.display = currentTab === 'all' ? '' : 'none';

    tbody.innerHTML = reports.map(r => {
        const content = (r.work_content || '').substring(0, 80);
        const ellipsis = (r.work_content || '').length > 80 ? '...' : '';
        return `
        <tr style="cursor:pointer;" onclick="location.href='/reports/${r.id}'">
            <td><span class="fw-bold">${r.report_date}</span></td>
            <td><span class="badge bg-info text-dark">${escapeHtml(categoryMap[r.category_id] || '-')}</span></td>
            <td>${escapeHtml(r.task_name || '')}</td>
            <td class="text-end"><span class="badge bg-light text-dark border">${formatMinutes(r.time_minutes)}</span></td>
            <td><small class="text-muted">${escapeHtml(content)}${ellipsis}</small></td>
            ${currentTab === 'all' ? '<td><small class="text-muted">' + escapeHtml(allUsers[r.user_id] || 'Unknown') + '</small></td>' : ''}
        </tr>`;
    }).join('');
}

function switchTab(tab, el) {
    currentTab = tab;
    document.querySelectorAll('.nav-tabs .nav-link').forEach(a => a.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('filter-date').value = todayStr();
    loadReports();
}

function searchByDate() {
    loadReports();
}

function clearDateFilter() {
    document.getElementById('filter-date').value = todayStr();
    loadReports();
}

function populateCategorySelect(selectId, selectedId) {
    const sel = document.getElementById(selectId);
    sel.innerHTML = '<option value="">-- 選択 --</option>' +
        allCategories.map(c => `<option value="${c.id}" ${c.id === selectedId ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
}

function openNewReport() {
    document.getElementById('reportModalTitle').textContent = 'New Report';
    document.getElementById('report-id').value = '';
    document.getElementById('report-date').value = todayStr();
    document.getElementById('report-task-name').value = '';
    document.getElementById('report-time-minutes').value = '0';
    document.getElementById('report-work-content').value = '';
    document.getElementById('report-achievements').value = '';
    document.getElementById('report-issues').value = '';
    document.getElementById('report-next-plan').value = '';
    document.getElementById('report-remarks').value = '';
    populateCategorySelect('report-category', null);
}

async function saveReport() {
    const id = document.getElementById('report-id').value;
    const categoryId = parseInt(document.getElementById('report-category').value);
    const taskName = document.getElementById('report-task-name').value;
    const data = {
        report_date: document.getElementById('report-date').value,
        category_id: categoryId,
        task_name: taskName,
        time_minutes: parseInt(document.getElementById('report-time-minutes').value) || 0,
        work_content: document.getElementById('report-work-content').value,
        achievements: document.getElementById('report-achievements').value || null,
        issues: document.getElementById('report-issues').value || null,
        next_plan: document.getElementById('report-next-plan').value || null,
        remarks: document.getElementById('report-remarks').value || null,
    };

    if (!data.report_date) return alert('Date is required');
    if (!categoryId) return alert('タスク分類 is required');
    if (!taskName) return alert('タスク名 is required');
    if (!data.work_content) return alert('Work content is required');

    try {
        if (id) {
            await api.put(`/api/reports/${id}`, data);
        } else {
            await api.post('/api/reports/', data);
        }
        bootstrap.Modal.getInstance(document.getElementById('reportModal')).hide();
        loadReports();
    } catch (e) {
        alert(e.message);
    }
}

// Enter key on date input triggers search
document.getElementById('filter-date').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') searchByDate();
});

document.getElementById('filter-date').value = todayStr();
loadReports();
