function _getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

const api = {
    async request(url, options = {}) {
        const defaultHeaders = { 'Content-Type': 'application/json', 'X-CSRF-Token': _getCsrfToken() };
        const config = {
            headers: { ...defaultHeaders, ...options.headers },
            ...options,
        };
        // Content-Type 不要な場合（DELETE等body無し）の処理
        if (!config.body) delete config.headers['Content-Type'];

        const res = await fetch(url, config);
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: res.statusText }));
            let message;
            if (Array.isArray(error.detail)) {
                message = error.detail.map(e => e.msg || String(e)).join('; ');
            } else {
                message = error.detail || `HTTP ${res.status}`;
            }
            throw new Error(message);
        }
        if (res.status === 204) return null;
        return res.json();
    },

    get(url) { return this.request(url); },
    post(url, data) { return this.request(url, { method: 'POST', body: JSON.stringify(data) }); },
    put(url, data) { return this.request(url, { method: 'PUT', body: JSON.stringify(data) }); },
    patch(url, data) { return this.request(url, { method: 'PATCH', body: data ? JSON.stringify(data) : undefined }); },
    del(url) { return this.request(url, { method: 'DELETE' }); },

    async logout() {
        await this.request('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    },
};
