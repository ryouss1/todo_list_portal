let currentUserRole = null;
let currentUserId = null;
let allGroups = [];
let groupMap = {};

async function init() {
    try {
        const me = await api.get('/api/auth/me');
        currentUserRole = me.role;
        currentUserId = me.user_id;
        if (currentUserRole === 'admin') {
            document.getElementById('btn-add-user').classList.remove('d-none');
            document.getElementById('group-section').classList.remove('d-none');
        }
    } catch (e) {
        // ignore
    }
    await loadGroups();
    await loadUsers();
}

async function loadGroups() {
    try {
        allGroups = await api.get('/api/groups/');
        groupMap = {};
        allGroups.forEach(g => { groupMap[g.id] = g.name; });
        buildGroupOptions();
        renderGroups();
    } catch (e) {
        // ignore
    }
}

function buildGroupOptions() {
    const sel = document.getElementById('edit-group-id');
    sel.innerHTML = `<option value="">-- ${i18n.t('None')} --</option>`;
    allGroups.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.name;
        sel.appendChild(opt);
    });
}

async function loadUsers() {
    try {
        const users = await api.get('/api/users/');
        const tbody = document.getElementById('user-list');
        tbody.innerHTML = users.map(u => {
            const groupName = u.group_name
                ? '<span class="badge bg-info text-dark">' + escapeHtml(u.group_name) + '</span>'
                : '<span class="text-muted">-</span>';
            const roleBadge = u.role === 'admin'
                ? '<span class="badge bg-danger">admin</span>'
                : '<span class="badge bg-secondary">user</span>';
            const statusBadge = u.is_active
                ? `<span class="badge bg-success">${i18n.t('Active')}</span>`
                : `<span class="badge bg-warning text-dark">${i18n.t('Inactive')}</span>`;
            let actions = '';
            if (currentUserRole === 'admin') {
                actions = `
                    <button class="btn btn-outline-primary btn-sm" onclick="openEditModal(${u.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-warning btn-sm" onclick="openResetModal(${u.id}, '${escapeHtml(u.email)}')">
                        <i class="bi bi-key"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="openDeleteModal(${u.id}, '${escapeHtml(u.email)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
            } else if (currentUserId == u.id) {
                actions = `
                    <button class="btn btn-outline-primary btn-sm" onclick="openSelfEditModal(${u.id}, '${escapeHtml(u.display_name)}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                `;
            }
            return `<tr>
                <td>${u.id}</td>
                <td>${escapeHtml(u.email)}</td>
                <td>${escapeHtml(u.display_name)}</td>
                <td>${groupName}</td>
                <td>${roleBadge}</td>
                <td>${statusBadge}</td>
                <td>${actions}</td>
            </tr>`;
        }).join('');
    } catch (e) {
        showToast(i18n.t('Failed to load users: {message}', {message: e.message}), 'error');
    }
}

async function createUser() {
    const email = document.getElementById('create-email').value.trim();
    const displayName = document.getElementById('create-display-name').value.trim();
    const password = document.getElementById('create-password').value;
    const role = document.getElementById('create-role').value;
    if (!email || !displayName || !password) return;
    try {
        await api.post('/api/users/', {
            email: email,
            display_name: displayName,
            password: password,
            role: role,
        });
        bootstrap.Modal.getInstance(document.getElementById('userCreateModal')).hide();
        document.getElementById('create-email').value = '';
        document.getElementById('create-display-name').value = '';
        document.getElementById('create-password').value = '';
        document.getElementById('create-role').value = 'user';
        showToast(i18n.t('User created'), 'success');
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to create user: {message}', {message: e.message}), 'error');
    }
}

function openEditModal(id) {
    const users = document.querySelectorAll('#user-list tr');
    // Fetch user details from API for accurate data
    api.get(`/api/users/${id}`).then(u => {
        document.getElementById('edit-user-id').value = u.id;
        document.getElementById('edit-email').value = u.email;
        document.getElementById('edit-display-name').value = u.display_name;
        document.getElementById('edit-role').value = u.role;
        document.getElementById('edit-is-active').checked = u.is_active;
        document.getElementById('edit-group-id').value = u.group_id || '';
        document.getElementById('edit-email-group').style.display = '';
        document.getElementById('edit-role-group').style.display = '';
        document.getElementById('edit-active-group').style.display = '';
        document.getElementById('edit-group-group').style.display = '';
        new bootstrap.Modal(document.getElementById('userEditModal')).show();
    });
}

function openSelfEditModal(id, displayName) {
    document.getElementById('edit-user-id').value = id;
    document.getElementById('edit-display-name').value = displayName;
    document.getElementById('edit-email-group').style.display = 'none';
    document.getElementById('edit-role-group').style.display = 'none';
    document.getElementById('edit-active-group').style.display = 'none';
    document.getElementById('edit-group-group').style.display = 'none';
    new bootstrap.Modal(document.getElementById('userEditModal')).show();
}

async function updateUser() {
    const id = document.getElementById('edit-user-id').value;
    const data = {
        display_name: document.getElementById('edit-display-name').value.trim(),
    };
    if (document.getElementById('edit-email-group').style.display !== 'none') {
        const email = document.getElementById('edit-email').value.trim();
        if (email) data.email = email;
    }
    if (document.getElementById('edit-role-group').style.display !== 'none') {
        data.role = document.getElementById('edit-role').value;
        data.is_active = document.getElementById('edit-is-active').checked;
    }
    if (document.getElementById('edit-group-group').style.display !== 'none') {
        const gid = document.getElementById('edit-group-id').value;
        data.group_id = gid ? parseInt(gid) : null;
    }
    try {
        await api.put(`/api/users/${id}`, data);
        bootstrap.Modal.getInstance(document.getElementById('userEditModal')).hide();
        showToast(i18n.t('User updated'), 'success');
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to update user: {message}', {message: e.message}), 'error');
    }
}

function openResetModal(id, email) {
    document.getElementById('reset-user-id').value = id;
    document.getElementById('reset-email').textContent = email;
    document.getElementById('reset-new-password').value = '';
    new bootstrap.Modal(document.getElementById('passwordResetModal')).show();
}

async function resetPassword() {
    const id = document.getElementById('reset-user-id').value;
    const newPassword = document.getElementById('reset-new-password').value;
    if (!newPassword) return;
    try {
        await api.put(`/api/users/${id}/password`, { new_password: newPassword });
        bootstrap.Modal.getInstance(document.getElementById('passwordResetModal')).hide();
        showToast(i18n.t('Password reset'), 'success');
    } catch (e) {
        showToast(i18n.t('Failed to reset password: {message}', {message: e.message}), 'error');
    }
}

function openDeleteModal(id, email) {
    document.getElementById('delete-user-id').value = id;
    document.getElementById('delete-email').textContent = email;
    new bootstrap.Modal(document.getElementById('userDeleteModal')).show();
}

async function deleteUser() {
    const id = document.getElementById('delete-user-id').value;
    try {
        await api.del(`/api/users/${id}`);
        bootstrap.Modal.getInstance(document.getElementById('userDeleteModal')).hide();
        showToast(i18n.t('User deleted'), 'success');
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to delete user: {message}', {message: e.message}), 'error');
    }
}

// --- Group Management ---

let editingGroupId = null;

function renderGroups() {
    const tbody = document.getElementById('group-list');
    if (!tbody) return;
    tbody.innerHTML = allGroups.map(g => {
        if (editingGroupId === g.id) return renderGroupEditRow(g);
        return `<tr>
            <td>${escapeHtml(g.name)}</td>
            <td>${g.description ? escapeHtml(g.description) : '<span class="text-muted">-</span>'}</td>
            <td><span class="badge bg-primary">${g.member_count}</span></td>
            <td>${g.sort_order}</td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="startEditGroup(${g.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteGroup(${g.id})" title="${i18n.t('Delete')}"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`;
    }).join('');

    if (editingGroupId === 'new') {
        tbody.insertAdjacentHTML('afterbegin', renderGroupEditRow(null));
    }
}

function renderGroupEditRow(g) {
    const isNew = !g;
    const id = isNew ? 'new' : g.id;
    const name = isNew ? '' : g.name;
    const desc = isNew ? '' : (g.description || '');
    const order = isNew ? 0 : g.sort_order;
    return `<tr class="table-warning">
        <td><input type="text" class="form-control form-control-sm" id="grp-name-${id}" value="${escapeHtml(name)}" placeholder="${i18n.t('Group name')} *"></td>
        <td><input type="text" class="form-control form-control-sm" id="grp-desc-${id}" value="${escapeHtml(desc)}" placeholder="${i18n.t('Description')}"></td>
        <td>${isNew ? '' : '<span class="badge bg-primary">' + g.member_count + '</span>'}</td>
        <td><input type="number" class="form-control form-control-sm" id="grp-order-${id}" value="${order}" style="width:70px"></td>
        <td>
            <button class="btn btn-success btn-sm" onclick="saveGroup('${id}')"><i class="bi bi-check-lg"></i></button>
            <button class="btn btn-secondary btn-sm" onclick="cancelGroupEdit()"><i class="bi bi-x-lg"></i></button>
        </td>
    </tr>`;
}

function startNewGroup() {
    editingGroupId = 'new';
    renderGroups();
    const el = document.getElementById('grp-name-new');
    if (el) el.focus();
}

function startEditGroup(id) {
    editingGroupId = id;
    renderGroups();
    const el = document.getElementById(`grp-name-${id}`);
    if (el) el.focus();
}

function cancelGroupEdit() {
    editingGroupId = null;
    renderGroups();
}

async function saveGroup(id) {
    const name = document.getElementById(`grp-name-${id}`).value.trim();
    if (!name) {
        document.getElementById(`grp-name-${id}`).classList.add('is-invalid');
        return;
    }
    const data = {
        name: name,
        description: document.getElementById(`grp-desc-${id}`).value.trim() || null,
        sort_order: parseInt(document.getElementById(`grp-order-${id}`).value) || 0,
    };
    try {
        if (id === 'new') {
            await api.post('/api/groups/', data);
            showToast(i18n.t('Group created'), 'success');
        } else {
            await api.put(`/api/groups/${id}`, data);
            showToast(i18n.t('Group updated'), 'success');
        }
        editingGroupId = null;
        await loadGroups();
        await loadUsers();
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

async function deleteGroup(id) {
    if (!confirm(i18n.t('Delete this group? Members will be unassigned.'))) return;
    try {
        await api.del(`/api/groups/${id}`);
        showToast(i18n.t('Group deleted'), 'success');
        await loadGroups();
        await loadUsers();
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

init();
