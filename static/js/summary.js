let currentPeriod = 'weekly';
let currentRefDate = new Date().toISOString().split('T')[0];

const CATEGORY_COLORS = [
    '#0d6efd', '#198754', '#ffc107', '#dc3545',
    '#6f42c1', '#fd7e14', '#20c997', '#e83e8c',
    '#6610f2', '#0dcaf0', '#84b6eb', '#a3cfbb',
    '#d4a017', '#8b4513', '#9b59b6', '#795548'
];

function buildColorMap(categories) {
    const map = {};
    categories.forEach((cat, i) => {
        map[cat.id] = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
    });
    return map;
}

async function init() {
    try {
        const groups = await api.get('/api/groups/');
        const sel = document.getElementById('group-filter');
        groups.forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.id;
            opt.textContent = g.name;
            sel.appendChild(opt);
        });
    } catch (e) {
        // ignore
    }
    loadSummary();
}

async function loadSummary() {
    let url = `/api/summary/?period=${currentPeriod}&ref_date=${currentRefDate}`;
    const groupId = document.getElementById('group-filter').value;
    if (groupId) url += `&group_id=${groupId}`;
    const data = await api.get(url);
    renderSummary(data);
}

function renderUserStatus(data, colorMap) {
    const userTable = document.getElementById('user-status-table');
    if (data.user_report_statuses.length === 0) {
        userTable.innerHTML = `<tr><td colspan="4" class="text-muted">${i18n.t('No users')}</td></tr>`;
        return;
    }
    userTable.innerHTML = data.user_report_statuses.map((u, idx) => {
        const nonZero = u.category_breakdown.filter(b => b.count > 0);
        const totalMin = nonZero.reduce((sum, b) => sum + (b.total_minutes || 0), 0);
        let barHtml = '';
        if (totalMin > 0 && nonZero.length > 0) {
            const segments = nonZero.filter(b => b.total_minutes > 0).map(b => {
                const pct = (b.total_minutes / totalMin * 100);
                const color = colorMap[b.category_id] || '#6c757d';
                const h = Math.floor(b.total_minutes / 60);
                const m = b.total_minutes % 60;
                const timeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
                return `<div class="progress-bar" style="width:${pct}%;background-color:${color}" title="${escapeHtml(b.category_name)}: ${timeStr}"></div>`;
            }).join('');
            barHtml = `<div class="progress" style="height:20px">${segments}</div>`;
        } else if (u.report_count > 0 && nonZero.length > 0) {
            const segments = nonZero.map(b => {
                const pct = (b.count / u.report_count * 100);
                const color = colorMap[b.category_id] || '#6c757d';
                return `<div class="progress-bar" style="width:${pct}%;background-color:${color}" title="${escapeHtml(b.category_name)}: ${b.count}"></div>`;
            }).join('');
            barHtml = `<div class="progress" style="height:20px">${segments}</div>`;
        }
        const detailId = `user-detail-${idx}`;
        let badges = nonZero.map(b => {
            const color = colorMap[b.category_id] || '#6c757d';
            const h = Math.floor((b.total_minutes || 0) / 60);
            const m = (b.total_minutes || 0) % 60;
            const timeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
            return `<span class="badge me-1 mb-1" style="background-color:${color}">${escapeHtml(b.category_name)}: ${b.count}${i18n.t('items')} (${timeStr})</span>`;
        }).join('');
        let row = `<tr class="cursor-pointer" data-bs-toggle="collapse" data-bs-target="#${detailId}">`;
        row += `<td>${escapeHtml(u.display_name)}</td>`;
        row += `<td>${barHtml}</td>`;
        row += `<td class="text-center"><span class="badge bg-primary">${u.report_count}</span></td>`;
        row += `<td class="text-center">${u.has_report_today ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-muted"></i>'}</td>`;
        row += '</tr>';
        if (nonZero.length > 0) {
            row += `<tr class="collapse detail-row" id="${detailId}"><td colspan="4"><div class="d-flex flex-wrap gap-1">${badges}</div></td></tr>`;
        }
        return row;
    }).join('');
}

function renderTrends(data, colorMap) {
    const legendEl = document.getElementById('trend-legend');
    const usedIds = new Set();
    (data.report_trends || []).forEach(t => {
        (t.category_breakdown || []).forEach(b => usedIds.add(b.category_id));
    });
    const usedCats = data.categories.filter(c => usedIds.has(c.id));
    if (usedCats.length > 0) {
        legendEl.innerHTML = '<div class="d-flex flex-wrap gap-1">' + usedCats.map(c =>
            `<span class="me-2"><span style="display:inline-block;width:12px;height:12px;background-color:${colorMap[c.id]};border-radius:2px;vertical-align:middle"></span> <small>${escapeHtml(c.name)}</small></span>`
        ).join('') + '</div>';
    } else {
        legendEl.innerHTML = '';
    }

    const trendEl = document.getElementById('trend-chart');
    if (data.report_trends.length === 0) {
        trendEl.innerHTML = `<div class="text-muted text-center">${i18n.t('No data')}</div>`;
    } else {
        const maxCount = Math.max(...data.report_trends.map(t => t.count));
        trendEl.innerHTML = data.report_trends.map(t => {
            let barsHtml = '';
            if (t.category_breakdown && t.category_breakdown.length > 0) {
                barsHtml = t.category_breakdown.map(b => {
                    const pct = (b.count / maxCount * 100);
                    const color = colorMap[b.category_id] || '#6c757d';
                    return `<div class="progress-bar" style="width:${pct}%;background-color:${color}" title="${escapeHtml(b.category_name)}: ${b.count}"></div>`;
                }).join('');
            } else {
                barsHtml = `<div class="progress-bar" style="width:${(t.count/maxCount*100)}%">${t.count}</div>`;
            }
            return `
                <div class="d-flex align-items-center mb-1">
                    <small class="text-muted me-2" style="width:80px">${t.date}</small>
                    <div class="progress flex-grow-1" style="height:20px">
                        ${barsHtml}
                    </div>
                    <small class="ms-1" style="width:24px;text-align:right">${t.count}</small>
                </div>
            `;
        }).join('');
    }
}

function renderSummary(data) {
    document.getElementById('period-label').textContent =
        `${data.period_start} ~ ${data.period_end}`;
    document.getElementById('total-reports').textContent =
        i18n.t('Total: {count} reports', {count: data.total_reports});

    const colorMap = buildColorMap(data.categories || []);

    renderUserStatus(data, colorMap);
    renderTrends(data, colorMap);

    const recentEl = document.getElementById('recent-reports');
    if (data.recent_reports.length === 0) {
        recentEl.innerHTML = `<div class="list-group-item text-muted">${i18n.t('No reports')}</div>`;
    } else {
        recentEl.innerHTML = data.recent_reports.map(r => `
            <a href="/reports/${r.id}" class="list-group-item list-group-item-action">
                <div class="d-flex justify-content-between">
                    <strong>${r.report_date}</strong>
                    <small class="text-muted">${escapeHtml(r.display_name)}</small>
                </div>
                <small class="text-muted">${escapeHtml(r.work_content_preview)}</small>
            </a>
        `).join('');
    }

    const catTable = document.getElementById('category-table');
    if (data.category_trends.length === 0) {
        catTable.innerHTML = `<tr><td colspan="3" class="text-muted">${i18n.t('No data')}</td></tr>`;
    } else {
        catTable.innerHTML = data.category_trends.map(c => {
            const h = Math.floor(c.total_minutes / 60);
            const m = c.total_minutes % 60;
            const timeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
            return `
                <tr>
                    <td>${escapeHtml(c.category_name)}</td>
                    <td><span class="badge bg-primary">${c.report_count}</span></td>
                    <td>${timeStr}</td>
                </tr>
            `;
        }).join('');
    }

    const issuesEl = document.getElementById('issues-list');
    if (data.issues.length === 0) {
        issuesEl.innerHTML = `<div class="list-group-item text-muted">${i18n.t('No issues reported')}</div>`;
    } else {
        issuesEl.innerHTML = data.issues.map(i => `
            <div class="list-group-item">
                <small>${escapeHtml(i)}</small>
            </div>
        `).join('');
    }
}

function setPeriod(period) {
    currentPeriod = period;
    document.getElementById('btn-daily').classList.toggle('active', period === 'daily');
    document.getElementById('btn-weekly').classList.toggle('active', period === 'weekly');
    document.getElementById('btn-monthly').classList.toggle('active', period === 'monthly');
    loadSummary();
}

function navigate(direction) {
    const d = new Date(currentRefDate);
    if (currentPeriod === 'daily') {
        d.setDate(d.getDate() + direction);
    } else if (currentPeriod === 'weekly') {
        d.setDate(d.getDate() + (direction * 7));
    } else {
        d.setMonth(d.getMonth() + direction);
    }
    currentRefDate = d.toISOString().split('T')[0];
    loadSummary();
}

function goToday() {
    currentRefDate = new Date().toISOString().split('T')[0];
    loadSummary();
}

init();
