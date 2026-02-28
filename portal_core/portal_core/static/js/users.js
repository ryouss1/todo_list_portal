let currentUserRole = null;
let currentUserId = null;
let allDepartments = [];
let departmentMap = {};
let allRoles = [];

async function init() {
    try {
        const me = await api.get('/api/auth/me');
        currentUserRole = me.role;
        currentUserId = me.user_id;
        if (currentUserRole === 'admin') {
            document.getElementById('btn-add-user').classList.remove('d-none');
            document.getElementById('department-section').classList.remove('d-none');
        }
    } catch (e) {
        // ignore
    }
    await loadDepartments();
    await loadRoles();
    await loadUsers();
}

async function loadDepartments() {
    try {
        allDepartments = await api.get('/api/departments/');
        departmentMap = {};
        allDepartments.forEach(dept => { departmentMap[dept.id] = dept.name; });
        buildDepartmentOptions();
        renderDepartments();
    } catch (e) {
        // ignore
    }
}

function buildDepartmentOptions() {
    ['edit-department-id', 'create-department-id'].forEach(selId => {
        const sel = document.getElementById(selId);
        if (!sel) return;
        sel.innerHTML = `<option value="">-- ${i18n.t('None')} --</option>`;
        allDepartments.forEach(dept => {
            const opt = document.createElement('option');
            opt.value = dept.id;
            opt.textContent = dept.name;
            sel.appendChild(opt);
        });
    });
}

function buildParentOptions(currentParentId, excludeId) {
    let opts = `<option value="">-- ${i18n.t('None')} --</option>`;
    allDepartments.forEach(d => {
        if (d.id === excludeId) return;
        const sel = d.id === currentParentId ? ' selected' : '';
        opts += `<option value="${escapeHtml(String(d.id))}"${sel}>${escapeHtml(d.name)}</option>`;
    });
    return opts;
}

async function loadUsers() {
    try {
        const users = await api.get('/api/users/');
        const tbody = document.getElementById('user-list');
        tbody.innerHTML = users.map(u => {
            const groupName = u.department_name
                ? '<span class="badge bg-info text-dark">' + escapeHtml(u.department_name) + '</span>'
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
                    <button class="btn btn-outline-primary btn-sm" onclick="openEditModal(${u.id})" title="${i18n.t('Edit')}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" onclick="openUserRolesModal(${u.id}, '${escapeHtml(u.display_name)}')" title="${i18n.t('Roles')}">
                        <i class="bi bi-shield-check"></i>
                    </button>
                    <button class="btn btn-outline-warning btn-sm" onclick="openResetModal(${u.id}, '${escapeHtml(u.email)}')" title="${i18n.t('Reset Password')}">
                        <i class="bi bi-key"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="openDeleteModal(${u.id}, '${escapeHtml(u.email)}')" title="${i18n.t('Delete')}">
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
        const deptId = document.getElementById('create-department-id').value;
        await api.post('/api/users/', {
            email: email,
            display_name: displayName,
            password: password,
            role: role,
            department_id: deptId ? parseInt(deptId) : null,
        });
        bootstrap.Modal.getInstance(document.getElementById('userCreateModal')).hide();
        document.getElementById('create-email').value = '';
        document.getElementById('create-display-name').value = '';
        document.getElementById('create-password').value = '';
        document.getElementById('create-role').value = 'user';
        document.getElementById('create-department-id').value = '';
        showToast(i18n.t('User created'), 'success');
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to create user: {message}', {message: e.message}), 'error');
    }
}

function openEditModal(id) {
    // Fetch user details from API for accurate data
    api.get(`/api/users/${id}`).then(u => {
        document.getElementById('edit-user-id').value = u.id;
        document.getElementById('edit-email').value = u.email;
        document.getElementById('edit-display-name').value = u.display_name;
        document.getElementById('edit-role').value = u.role;
        document.getElementById('edit-is-active').checked = u.is_active;
        document.getElementById('edit-department-id').value = u.department_id || '';
        document.getElementById('edit-email-group').style.display = '';
        document.getElementById('edit-role-group').style.display = '';
        document.getElementById('edit-active-group').style.display = '';
        document.getElementById('edit-department-group').style.display = '';
        new bootstrap.Modal(document.getElementById('userEditModal')).show();
    });
}

function openSelfEditModal(id, displayName) {
    document.getElementById('edit-user-id').value = id;
    document.getElementById('edit-display-name').value = displayName;
    document.getElementById('edit-email-group').style.display = 'none';
    document.getElementById('edit-role-group').style.display = 'none';
    document.getElementById('edit-active-group').style.display = 'none';
    document.getElementById('edit-department-group').style.display = 'none';
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
    if (document.getElementById('edit-department-group').style.display !== 'none') {
        const did = document.getElementById('edit-department-id').value;
        data.department_id = did ? parseInt(did) : null;
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

// --- RBAC Role Management ---

async function loadRoles() {
    try {
        allRoles = await api.get('/api/roles/');
    } catch (e) {
        allRoles = [];
    }
}

async function openUserRolesModal(userId, displayName) {
    document.getElementById('roles-modal-user-id').value = userId;
    document.getElementById('roles-modal-user').textContent = displayName;

    // Populate add-role dropdown
    const sel = document.getElementById('roles-add-select');
    sel.innerHTML = `<option value="">-- ${i18n.t('Select role to add')} --</option>`;
    allRoles.filter(r => r.is_active).forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.display_name;
        sel.appendChild(opt);
    });

    await refreshUserRolesList(userId);
    new bootstrap.Modal(document.getElementById('userRolesModal')).show();
}

async function refreshUserRolesList(userId) {
    const container = document.getElementById('user-roles-list');
    try {
        const roles = await api.get(`/api/users/${userId}/roles`);
        if (!roles.length) {
            container.innerHTML = `<p class="text-muted small">${i18n.t('No roles assigned')}</p>`;
            return;
        }
        container.innerHTML = roles.map(r => `
            <span class="badge bg-primary me-1 mb-1" style="font-size:0.85em">
                ${escapeHtml(r.display_name)}
                <button class="btn-close btn-close-white ms-1" style="font-size:0.6em"
                    onclick="revokeRole(${userId}, ${r.id})" title="${i18n.t('Remove')}"></button>
            </span>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="text-danger small">${escapeHtml(e.message)}</p>`;
    }
}

async function assignRole() {
    const userId = document.getElementById('roles-modal-user-id').value;
    const roleId = document.getElementById('roles-add-select').value;
    if (!roleId) return;
    try {
        await api.post(`/api/users/${userId}/roles`, { role_id: parseInt(roleId) });
        document.getElementById('roles-add-select').value = '';
        await refreshUserRolesList(userId);
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

async function revokeRole(userId, roleId) {
    try {
        await api.del(`/api/users/${userId}/roles/${roleId}`);
        await refreshUserRolesList(userId);
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// --- Department Management ---

let editingDepartmentId = null;

function renderDepartments() {
    const tbody = document.getElementById('department-list');
    if (!tbody) return;
    tbody.innerHTML = allDepartments.map(dept => {
        if (editingDepartmentId === dept.id) return renderDepartmentEditRow(dept);
        const parentName = dept.parent_id
            ? escapeHtml(departmentMap[dept.parent_id] || '?')
            : '<span class="text-muted">—</span>';
        const activeBadge = dept.is_active
            ? `<span class="badge bg-success">${i18n.t('Active')}</span>`
            : `<span class="badge bg-warning text-dark">${i18n.t('Inactive')}</span>`;
        return `<tr>
            <td>${escapeHtml(dept.name)}</td>
            <td>${parentName}</td>
            <td>${dept.description ? escapeHtml(dept.description) : '<span class="text-muted">-</span>'}</td>
            <td><span class="badge bg-primary">${dept.member_count}</span></td>
            <td>${dept.sort_order}</td>
            <td>${activeBadge}</td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="startEditDepartment(${dept.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteDepartment(${dept.id})" title="${i18n.t('Delete')}"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`;
    }).join('');

    if (editingDepartmentId === 'new') {
        tbody.insertAdjacentHTML('afterbegin', renderDepartmentEditRow(null));
    }
}

function renderDepartmentEditRow(dept) {
    const isNew = !dept;
    const id = isNew ? 'new' : dept.id;
    const name = isNew ? '' : dept.name;
    const desc = isNew ? '' : (dept.description || '');
    const order = isNew ? 0 : dept.sort_order;
    const parentId = isNew ? null : dept.parent_id;
    const isActive = isNew ? true : dept.is_active;
    const excludeId = isNew ? null : dept.id;
    return `<tr class="table-warning">
        <td><input type="text" class="form-control form-control-sm" id="grp-name-${id}" value="${escapeHtml(name)}" placeholder="${i18n.t('Department name')} *"></td>
        <td>
            <select class="form-select form-select-sm" id="grp-parent-${id}">
                ${buildParentOptions(parentId, excludeId)}
            </select>
        </td>
        <td><input type="text" class="form-control form-control-sm" id="grp-desc-${id}" value="${escapeHtml(desc)}" placeholder="${i18n.t('Description')}"></td>
        <td>${isNew ? '' : '<span class="badge bg-primary">' + dept.member_count + '</span>'}</td>
        <td><input type="number" class="form-control form-control-sm" id="grp-order-${id}" value="${order}" style="width:70px"></td>
        <td>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="grp-active-${id}"${isActive ? ' checked' : ''}>
            </div>
        </td>
        <td>
            <button class="btn btn-success btn-sm" onclick="saveDepartment('${id}')"><i class="bi bi-check-lg"></i></button>
            <button class="btn btn-secondary btn-sm" onclick="cancelDepartmentEdit()"><i class="bi bi-x-lg"></i></button>
        </td>
    </tr>`;
}

function startNewDepartment() {
    editingDepartmentId = 'new';
    renderDepartments();
    const el = document.getElementById('grp-name-new');
    if (el) el.focus();
}

function startEditDepartment(id) {
    editingDepartmentId = id;
    renderDepartments();
    const el = document.getElementById(`grp-name-${id}`);
    if (el) el.focus();
}

function cancelDepartmentEdit() {
    editingDepartmentId = null;
    renderDepartments();
}

async function saveDepartment(id) {
    const name = document.getElementById(`grp-name-${id}`).value.trim();
    if (!name) {
        document.getElementById(`grp-name-${id}`).classList.add('is-invalid');
        return;
    }
    const pid = document.getElementById(`grp-parent-${id}`).value;
    const data = {
        name: name,
        description: document.getElementById(`grp-desc-${id}`).value.trim() || null,
        sort_order: parseInt(document.getElementById(`grp-order-${id}`).value) || 0,
        parent_id: pid ? parseInt(pid) : null,
        is_active: document.getElementById(`grp-active-${id}`).checked,
    };
    try {
        if (id === 'new') {
            await api.post('/api/departments/', data);
            showToast(i18n.t('Department created'), 'success');
        } else {
            await api.put(`/api/departments/${id}`, data);
            showToast(i18n.t('Department updated'), 'success');
        }
        editingDepartmentId = null;
        await loadDepartments();
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to save department: {message}', {message: e.message}), 'danger');
    }
}

async function deleteDepartment(id) {
    if (!confirm(i18n.t('Delete this department? Members will be unassigned.'))) return;
    try {
        await api.del(`/api/departments/${id}`);
        showToast(i18n.t('Department deleted'), 'success');
        await loadDepartments();
        await loadUsers();
    } catch (e) {
        showToast(i18n.t('Failed to delete department: {message}', {message: e.message}), 'danger');
    }
}

init();
