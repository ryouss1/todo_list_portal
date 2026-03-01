// Self-service menu visibility settings modal

const menuSettings = {
    _allMenus: [],
    _myVisibility: {},

    async load() {
        const body = document.getElementById('menuSettingsBody');
        body.innerHTML = '<div class="text-muted small">読み込み中...</div>';

        try {
            const [menus, myOverrides] = await Promise.all([
                api.get('/api/menus/my'),
                api.get('/api/menus/my-visibility'),
            ]);
            this._allMenus = menus;
            this._myVisibility = Object.fromEntries(myOverrides.map(r => [r.menu_id, r.kino_kbn]));
            this._render(body);
        } catch (e) {
            body.innerHTML = '<div class="text-danger">取得失敗</div>';
        }
    },

    _render(body) {
        if (!this._allMenus.length) {
            body.innerHTML = '<div class="text-muted small">メニューなし</div>';
            return;
        }
        let html = '<div class="list-group list-group-flush">';
        for (const menu of this._allMenus) {
            const kino = this._myVisibility[menu.id];
            const checked = kino !== 0 ? 'checked' : '';  // default show unless explicitly hidden
            html += `<div class="list-group-item d-flex align-items-center gap-2 px-0">
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input" type="checkbox" id="ms-${menu.id}" ${checked}
                        data-menu-id="${menu.id}">
                </div>
                <label class="form-check-label mb-0" for="ms-${menu.id}">
                    <i class="bi ${escapeHtml(menu.icon)}"></i> ${escapeHtml(menu.label)}
                </label>
                ${kino !== undefined && kino !== null
                    ? `<button class="btn btn-link btn-sm p-0 ms-auto text-muted"
                        onclick="menuSettings.reset(${menu.id})" title="リセット">
                        <i class="bi bi-arrow-counterclockwise"></i>
                       </button>`
                    : ''}
            </div>`;
        }
        html += '</div>';
        body.innerHTML = html;
    },

    async save() {
        const checkboxes = document.querySelectorAll('#menuSettingsBody [data-menu-id]');
        const updates = [];
        for (const cb of checkboxes) {
            const menuId = parseInt(cb.dataset.menuId);
            const kino = cb.checked ? 1 : 0;
            updates.push(api.put('/api/menus/my-visibility', { menu_id: menuId, kino_kbn: kino }));
        }
        await Promise.all(updates);
        // Close modal and reload page to reflect changes
        bootstrap.Modal.getInstance(document.getElementById('menuSettingsModal')).hide();
        window.location.reload();
    },

    async reset(menuId) {
        await api.del(`/api/menus/my-visibility/${menuId}`);
        await this.load();
    },
};
