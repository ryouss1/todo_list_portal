let currentTab = 'mine';
let currentItems = [];
let categoryMap = {};
let userMap = {};
let currentUserId = null;

async function loadCategories() {
    const cats = await api.get('/api/task-categories/');
    categoryMap = {};
    const sel = document.getElementById('item-category');
    sel.innerHTML = '<option value="">-- None --</option>';
    cats.forEach(c => {
        categoryMap[c.id] = c.name;
        sel.innerHTML += `<option value="${c.id}">${escapeHtml(c.name)}</option>`;
    });
}

async function loadUsers() {
    const users = await api.get('/api/users/');
    userMap = {};
    users.forEach(u => { userMap[u.id] = u.display_name; });
}

async function loadCurrentUser() {
    const me = await api.get('/api/auth/me');
    currentUserId = me.user_id;
}

function statusBadge(status) {
    switch (status) {
        case 'in_progress': return '<span class="badge bg-primary">in_progress</span>';
        case 'done': return '<span class="badge bg-success">done</span>';
        default: return '<span class="badge bg-secondary">open</span>';
    }
}

function formatDuration(totalSeconds) {
    if (!totalSeconds) return '';
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

async function loadItems() {
    let url;
    if (currentTab === 'mine') {
        url = '/api/task-list/mine';
    } else {
        url = '/api/task-list/all';
    }
    currentItems = await api.get(url);
    renderItems(currentItems);
}

function renderItems(items) {
    const table = document.getElementById('item-table');
    const tbody = document.getElementById('item-tbody');
    const emptyEl = document.getElementById('item-list');
    const thAssignee = document.getElementById('th-assignee');

    if (items.length === 0) {
        table.style.display = 'none';
        emptyEl.innerHTML = '<div class="text-muted text-center py-4">No items found</div>';
        return;
    }

    emptyEl.innerHTML = '';
    table.style.display = '';
    thAssignee.style.display = currentTab === 'all' ? '' : 'none';

    tbody.innerHTML = items.map(item => {
        const catName = item.category_id && categoryMap[item.category_id]
            ? escapeHtml(categoryMap[item.category_id]) : '-';
        const dateStr = item.scheduled_date || '';
        const duration = formatDuration(item.total_seconds);
        const backlog = item.backlog_ticket_id
            ? `<a href="https://ottsystems.backlog.com/view/${escapeHtml(item.backlog_ticket_id)}" target="_blank" class="text-decoration-none"><i class="bi bi-link-45deg"></i>${escapeHtml(item.backlog_ticket_id)}</a>`
            : '';

        const assigneeName = item.assignee_id && userMap[item.assignee_id]
            ? escapeHtml(userMap[item.assignee_id]) : '<span class="text-muted">-</span>';

        // Action buttons
        let actions = '';
        const notDone = item.status !== 'done';

        if (currentTab === 'mine') {
            // Mine tab: Unassign, Start, Edit, Done, Delete
            actions += `<button class="btn btn-outline-secondary btn-sm" onclick="unassignItem(${item.id})" title="Unassign"><i class="bi bi-person-dash"></i></button> `;
            if (notDone) {
                actions += `<button class="btn btn-outline-primary btn-sm" onclick="startAsTask(${item.id})" title="Start"><i class="bi bi-play-fill"></i></button> `;
            }
        } else {
            // All tab: Assign/Unassign based on state
            if (!item.assignee_id) {
                actions += `<button class="btn btn-outline-success btn-sm" onclick="assignToMe(${item.id})" title="Assign to me"><i class="bi bi-person-plus"></i></button> `;
            } else if (item.assignee_id === currentUserId) {
                actions += `<button class="btn btn-outline-secondary btn-sm" onclick="unassignItem(${item.id})" title="Unassign"><i class="bi bi-person-dash"></i></button> `;
            }
            if (notDone && item.assignee_id) {
                actions += `<button class="btn btn-outline-primary btn-sm" onclick="startAsTask(${item.id})" title="Start"><i class="bi bi-play-fill"></i></button> `;
            }
        }
        actions += `<button class="btn btn-outline-primary btn-sm" onclick="openEditItem(${item.id})" title="Edit"><i class="bi bi-pencil"></i></button> `;
        if (notDone) {
            actions += `<button class="btn btn-outline-success btn-sm" onclick="markDone(${item.id})" title="Done"><i class="bi bi-check-lg"></i></button> `;
        }
        actions += `<button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${item.id})" title="Delete"><i class="bi bi-trash"></i></button>`;

        return `
        <tr>
            <td>${statusBadge(item.status)}</td>
            <td>${escapeHtml(item.title)}</td>
            <td><span class="badge bg-info text-dark">${catName}</span></td>
            <td>${escapeHtml(dateStr)}</td>
            <td class="text-end">${duration ? '<span class="badge bg-light text-dark border">' + escapeHtml(duration) + '</span>' : ''}</td>
            <td>${backlog}</td>
            ${currentTab === 'all' ? '<td><small>' + assigneeName + '</small></td>' : ''}
            <td class="text-nowrap">${actions}</td>
        </tr>`;
    }).join('');
}

function switchTab(tab, el) {
    currentTab = tab;
    document.querySelectorAll('.nav-tabs .nav-link').forEach(a => a.classList.remove('active'));
    el.classList.add('active');
    loadItems();
}

function openNewItem() {
    document.getElementById('itemModalTitle').textContent = 'New Item';
    document.getElementById('item-id').value = '';
    document.getElementById('item-title').value = '';
    document.getElementById('item-description').value = '';
    document.getElementById('item-scheduled-date').value = '';
    document.getElementById('item-category').value = '';
    document.getElementById('item-backlog-ticket').value = '';
}

function openEditItem(id) {
    const item = currentItems.find(x => x.id === id);
    if (!item) return;
    document.getElementById('itemModalTitle').textContent = 'Edit Item';
    document.getElementById('item-id').value = item.id;
    document.getElementById('item-title').value = item.title;
    document.getElementById('item-description').value = item.description || '';
    document.getElementById('item-scheduled-date').value = item.scheduled_date || '';
    document.getElementById('item-category').value = item.category_id || '';
    document.getElementById('item-backlog-ticket').value = item.backlog_ticket_id || '';
    new bootstrap.Modal(document.getElementById('itemModal')).show();
}

async function saveItem() {
    const id = document.getElementById('item-id').value;
    const catVal = document.getElementById('item-category').value;
    const data = {
        title: document.getElementById('item-title').value,
        description: document.getElementById('item-description').value || null,
        scheduled_date: document.getElementById('item-scheduled-date').value || null,
        category_id: catVal ? parseInt(catVal) : null,
        backlog_ticket_id: document.getElementById('item-backlog-ticket').value || null,
    };
    if (!data.title) return alert('Title is required');

    if (id) {
        await api.put(`/api/task-list/${id}`, data);
    } else {
        await api.post('/api/task-list/', data);
    }
    bootstrap.Modal.getInstance(document.getElementById('itemModal')).hide();
    loadItems();
}

async function deleteItem(id) {
    if (!confirm('Delete this item?')) return;
    await api.del(`/api/task-list/${id}`);
    loadItems();
}

async function assignToMe(id) {
    await api.post(`/api/task-list/${id}/assign`);
    loadItems();
}

async function unassignItem(id) {
    await api.post(`/api/task-list/${id}/unassign`);
    loadItems();
}

async function startAsTask(id) {
    try {
        const task = await api.post(`/api/task-list/${id}/start`);
        showToast(`Task "${escapeHtml(task.title)}" created in Tasks`, 'success');
        loadItems();
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

async function markDone(id) {
    await api.put(`/api/task-list/${id}`, { status: 'done' });
    loadItems();
}

// Initialize
Promise.all([loadCategories(), loadUsers(), loadCurrentUser()]).then(() => loadItems());
