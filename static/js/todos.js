let allTodos = [];
let currentFilter = 'all';

async function loadTodos() {
    allTodos = await api.get('/api/todos/');
    renderTodos();
}

function renderTodos() {
    let filtered = allTodos;
    if (currentFilter === 'active') filtered = allTodos.filter(t => !t.is_completed);
    if (currentFilter === 'completed') filtered = allTodos.filter(t => t.is_completed);

    const el = document.getElementById('todo-list');
    if (filtered.length === 0) {
        el.innerHTML = `<div class="text-muted text-center py-4">${i18n.t('No todos found')}</div>`;
        return;
    }
    el.innerHTML = filtered.map(t => `
        <div class="card mb-2 ${t.is_completed ? 'todo-completed' : ''}">
            <div class="card-body d-flex justify-content-between align-items-center py-2">
                <div class="d-flex align-items-center">
                    <input type="checkbox" class="form-check-input me-3" ${t.is_completed ? 'checked' : ''}
                        onchange="toggleTodo(${t.id})">
                    <div>
                        <span class="todo-title">${priorityBadge(t.priority)} ${visibilityBadge(t.visibility)} ${escapeHtml(t.title)}</span>
                        ${t.description ? '<br><small class="text-muted">' + escapeHtml(t.description) + '</small>' : ''}
                        ${t.due_date ? '<br><small class="text-muted"><i class="bi bi-calendar"></i> ' + t.due_date + '</small>' : ''}
                    </div>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="openEditTodo(${t.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteTodo(${t.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterTodos(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderTodos();
}

function openNewTodo() {
    document.getElementById('todoModalTitle').textContent = i18n.t('New Todo');
    document.getElementById('todo-id').value = '';
    document.getElementById('todo-title').value = '';
    document.getElementById('todo-description').value = '';
    document.getElementById('todo-priority').value = '0';
    document.getElementById('todo-due-date').value = '';
    document.getElementById('todo-visibility').value = 'private';
}

function openEditTodo(id) {
    const t = allTodos.find(x => x.id === id);
    if (!t) return;
    document.getElementById('todoModalTitle').textContent = i18n.t('Edit Todo');
    document.getElementById('todo-id').value = t.id;
    document.getElementById('todo-title').value = t.title;
    document.getElementById('todo-description').value = t.description || '';
    document.getElementById('todo-priority').value = t.priority;
    document.getElementById('todo-due-date').value = t.due_date || '';
    document.getElementById('todo-visibility').value = t.visibility || 'private';
    new bootstrap.Modal(document.getElementById('todoModal')).show();
}

async function saveTodo() {
    const id = document.getElementById('todo-id').value;
    const data = {
        title: document.getElementById('todo-title').value,
        description: document.getElementById('todo-description').value || null,
        priority: parseInt(document.getElementById('todo-priority').value),
        due_date: document.getElementById('todo-due-date').value || null,
        visibility: document.getElementById('todo-visibility').value,
    };

    if (!data.title) return alert(i18n.t('Title is required'));

    if (id) {
        await api.put(`/api/todos/${id}`, data);
    } else {
        await api.post('/api/todos/', data);
    }
    bootstrap.Modal.getInstance(document.getElementById('todoModal')).hide();
    loadTodos();
}

async function toggleTodo(id) {
    await api.patch(`/api/todos/${id}/toggle`);
    loadTodos();
}

async function deleteTodo(id) {
    if (!confirm(i18n.t('Delete this todo?'))) return;
    await api.del(`/api/todos/${id}`);
    loadTodos();
}

function priorityBadge(p) {
    if (p === 2) return `<span class="badge bg-danger">${i18n.t('Urgent')}</span>`;
    if (p === 1) return `<span class="badge bg-warning text-dark">${i18n.t('High')}</span>`;
    return '';
}

function visibilityBadge(v) {
    if (v === 'public') return `<span class="badge bg-info">${i18n.t('Public')}</span>`;
    return '';
}

loadTodos();
