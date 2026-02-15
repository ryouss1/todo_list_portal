let userMap = {};

async function loadPublicTodos() {
    const [todos, users] = await Promise.all([
        api.get('/api/todos/public'),
        api.get('/api/users/')
    ]);

    users.forEach(u => { userMap[u.id] = u.display_name; });

    const el = document.getElementById('public-todo-list');
    if (todos.length === 0) {
        el.innerHTML = '<div class="text-muted text-center py-4">No public todos</div>';
        return;
    }
    el.innerHTML = todos.map(t => `
        <div class="card mb-2 ${t.is_completed ? 'todo-completed' : ''}">
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="todo-title">${priorityBadge(t.priority)} ${escapeHtml(t.title)}</span>
                        <small class="text-muted ms-2">by ${escapeHtml(userMap[t.user_id] || 'Unknown')}</small>
                        ${t.description ? '<br><small class="text-muted">' + escapeHtml(t.description) + '</small>' : ''}
                        ${t.due_date ? '<br><small class="text-muted"><i class="bi bi-calendar"></i> ' + t.due_date + '</small>' : ''}
                    </div>
                    <div>
                        ${t.is_completed ? '<span class="badge bg-success">Done</span>' : '<span class="badge bg-secondary">Active</span>'}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function priorityBadge(p) {
    if (p === 2) return '<span class="badge bg-danger">Urgent</span>';
    if (p === 1) return '<span class="badge bg-warning text-dark">High</span>';
    return '';
}

loadPublicTodos();
