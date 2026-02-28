// App-specific shared utilities (not part of portal_core)

// カテゴリキャッシュ
let _categoryCache = null;

async function getCategories() {
    if (!_categoryCache) {
        _categoryCache = await api.get('/api/task-categories/');
    }
    return _categoryCache;
}
