// ===== Log Sources Dashboard (Table) + Real-time Log Stream =====

let sources = [];
let currentUser = null;
let allLogs = [];
let currentFilter = "all";
let ws = null;
let editingSourceId = null;
let allDepartments = [];

// ===== Initialisation =====

async function init() {
    try {
        currentUser = await api.get("/api/auth/me");
    } catch (e) {
        currentUser = null;
    }

    // Show admin-only controls
    if (currentUser && currentUser.role === "admin") {
        var btn = document.getElementById("btn-new-source");
        if (btn) btn.classList.remove("d-none");
        var btnEmpty = document.getElementById("btn-new-source-empty");
        if (btnEmpty) btnEmpty.classList.remove("d-none");
    }

    // Collapse chevron toggle
    var streamSection = document.getElementById("logStreamSection");
    if (streamSection) {
        streamSection.addEventListener("show.bs.collapse", function () {
            var chevron = document.getElementById("log-stream-chevron");
            if (chevron) {
                chevron.classList.remove("bi-chevron-down");
                chevron.classList.add("bi-chevron-up");
            }
        });
        streamSection.addEventListener("hide.bs.collapse", function () {
            var chevron = document.getElementById("log-stream-chevron");
            if (chevron) {
                chevron.classList.remove("bi-chevron-up");
                chevron.classList.add("bi-chevron-down");
            }
        });
    }

    await loadDepartments();
    await loadSources();
    loadLogs();
    connectWebSocket();
}

// ===== Departments =====

async function loadDepartments() {
    try {
        allDepartments = await api.get("/api/departments/");
    } catch (e) {
        allDepartments = [];
    }
    var sel = document.getElementById("source-department-id");
    if (sel) {
        // Keep first placeholder option, remove the rest
        while (sel.options.length > 1) sel.remove(1);
        for (var i = 0; i < allDepartments.length; i++) {
            var opt = document.createElement("option");
            opt.value = allDepartments[i].id;
            opt.textContent = allDepartments[i].name;
            sel.appendChild(opt);
        }
    }
}

function getDepartmentName(deptId) {
    for (var i = 0; i < allDepartments.length; i++) {
        if (allDepartments[i].id === deptId) return allDepartments[i].name;
    }
    return "";
}

// ===== Source Dashboard (Table) =====

async function loadSources() {
    try {
        sources = await api.get("/api/log-sources/status");
    } catch (e) {
        sources = [];
    }
    renderSourceTable(sources);
}

function renderSourceTable(list) {
    var tbody = document.getElementById("source-tbody");
    var emptyEl = document.getElementById("source-cards-empty");
    var tableWrap = document.getElementById("source-table-wrap");

    if (!list || list.length === 0) {
        tbody.innerHTML = "";
        tableWrap.classList.add("d-none");
        emptyEl.classList.remove("d-none");
        return;
    }

    emptyEl.classList.add("d-none");
    tableWrap.classList.remove("d-none");
    var isAdmin = currentUser && currentUser.role === "admin";

    var rows = [];
    for (var i = 0; i < list.length; i++) {
        var s = list[i];

        // Status dot: has_alert (file changes) > errors > enabled > disabled
        var statusDot;
        if (s.has_alert) {
            statusDot = '<span class="d-inline-block rounded-circle bg-danger" style="width:10px;height:10px" title="' + i18n.t("File changes detected") + '"></span>';
        } else if (s.consecutive_errors > 0) {
            statusDot = '<span class="d-inline-block rounded-circle bg-danger" style="width:10px;height:10px" title="' + i18n.t("Error") + '"></span>';
        } else if (s.is_enabled) {
            statusDot = '<span class="d-inline-block rounded-circle bg-success" style="width:10px;height:10px" title="' + i18n.t("Enabled") + '"></span>';
        } else {
            statusDot = '<span class="d-inline-block rounded-circle bg-secondary" style="width:10px;height:10px" title="' + i18n.t("Disabled") + '"></span>';
        }

        // Access method badge
        var methodBadge;
        if (s.access_method === "smb") {
            methodBadge = '<span class="badge" style="background-color:#6f42c1">' + escapeHtml(s.access_method.toUpperCase()) + "</span>";
        } else {
            methodBadge = '<span class="badge bg-primary">' + escapeHtml(s.access_method.toUpperCase()) + "</span>";
        }

        // File count with badges (only show new/upd when alert_on_change is enabled)
        var fileBadges = '<span class="text-muted">' + s.file_count + "</span>";
        if (s.alert_on_change && s.new_file_count > 0) {
            fileBadges += ' <span class="badge bg-primary" style="font-size:0.65rem">' + s.new_file_count + " " + i18n.t("new") + "</span>";
        }
        if (s.alert_on_change && s.updated_file_count > 0) {
            fileBadges += ' <span class="badge bg-warning text-dark" style="font-size:0.65rem">' + s.updated_file_count + " " + i18n.t("upd") + "</span>";
        }

        // Last checked
        var lastChecked = s.last_checked_at
            ? '<small class="text-muted">' + new Date(s.last_checked_at).toLocaleString() + "</small>"
            : '<small class="text-muted">-</small>';

        // Action buttons
        var actions = '<div class="btn-group btn-group-sm">';
        actions += '<button class="btn btn-outline-primary" onclick="viewFiles(' + s.id + ')" title="' + i18n.t("View Files") + '">'
            + '<i class="bi bi-files"></i></button>';
        if (isAdmin) {
            actions += '<button class="btn btn-outline-success" onclick="scanSource(' + s.id + ')" title="' + i18n.t("Scan") + '">'
                + '<i class="bi bi-arrow-repeat"></i></button>';
            actions += '<button class="btn btn-outline-secondary" onclick="openEditSource(' + s.id + ')" title="' + i18n.t("Edit") + '">'
                + '<i class="bi bi-pencil"></i></button>';
            actions += '<button class="btn btn-outline-info" onclick="testConnection(' + s.id + ')" title="' + i18n.t("Test Connection") + '">'
                + '<i class="bi bi-plug"></i></button>';
            actions += '<button class="btn btn-outline-danger" onclick="deleteSource(' + s.id + ')" title="' + i18n.t("Delete") + '">'
                + '<i class="bi bi-trash"></i></button>';
        }
        actions += "</div>";

        // Main row
        var row = "<tr>"
            + "<td>" + statusDot + "</td>"
            + "<td><strong>" + escapeHtml(s.name) + "</strong>"
            + ' <span class="badge bg-info text-dark" style="font-size:0.65rem">' + escapeHtml(s.source_type) + "</span></td>"
            + "<td><small>" + escapeHtml(s.department_name || "") + '</small> <small class="font-monospace text-muted">' + escapeHtml(s.host) + "</small></td>"
            + "<td>" + methodBadge + "</td>"
            + '<td class="text-center">' + (s.path_count || 0) + "</td>"
            + '<td><small class="text-muted">' + escapeHtml(s.collection_mode) + "</small></td>"
            + '<td class="text-center">' + fileBadges + "</td>"
            + "<td>" + lastChecked + "</td>"
            + '<td class="text-end">' + actions + "</td>"
            + "</tr>";
        rows.push(row);

        // Alert sub-row: folder links + changed file names
        if (s.has_alert && s.changed_paths && s.changed_paths.length > 0) {
            var alertRow = '<tr class="table-danger">'
                + '<td colspan="9" class="py-2 ps-4">'
                + '<i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>'
                + '<strong class="text-danger">' + i18n.t("File changes detected") + "</strong>";
            for (var j = 0; j < s.changed_paths.length; j++) {
                var cp = s.changed_paths[j];
                var allChanged = (cp.new_files || []).concat(cp.updated_files || []);
                var copyPath = cp.copy_path || cp.folder_link;
                alertRow += '<div class="ms-3 mt-1">'
                    + '<span class="text-decoration-none font-monospace small copy-path-btn" role="button" '
                    + 'data-copy-path="' + escapeHtml(copyPath) + '" title="' + i18n.t("Click to copy path") + '">'
                    + '<i class="bi bi-folder2-open"></i> ' + escapeHtml(cp.base_path)
                    + ' <i class="bi bi-clipboard ms-1 text-muted small"></i>'
                    + '</span>';
                if (allChanged.length > 0) {
                    alertRow += ' <small class="text-muted">(' + allChanged.map(escapeHtml).join(", ") + ')</small>';
                }
                alertRow += '</div>';
            }
            alertRow += "</td></tr>";
            rows.push(alertRow);
        }

        // Error detail row
        if (s.consecutive_errors > 0 && s.last_error) {
            var errRow = '<tr class="table-danger">'
                + '<td colspan="9" class="py-1 ps-4">'
                + '<i class="bi bi-exclamation-triangle text-danger"></i> '
                + '<small><strong>' + i18n.t("Errors") + ": " + s.consecutive_errors + "</strong> &mdash; "
                + escapeHtml(truncateText(s.last_error, 120)) + "</small>"
                + "</td></tr>";
            rows.push(errRow);
        }
    }
    tbody.innerHTML = rows.join("");
}

// ===== Source CRUD =====

function openNewSource() {
    editingSourceId = null;
    document.getElementById("sourceModalTitle").innerHTML =
        '<i class="bi bi-hdd-network"></i> ' + i18n.t("New Source");
    resetSourceForm();
    toggleParserTab();
    // Reset to Connection tab
    var firstTab = document.querySelector("#sourceModal .stl-tabs .nav-link");
    if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
}

async function openEditSource(id) {
    var source;
    try {
        source = await api.get("/api/log-sources/" + id);
    } catch (e) {
        showToast(e.message, "danger");
        return;
    }

    editingSourceId = source.id;
    document.getElementById("sourceModalTitle").innerHTML =
        '<i class="bi bi-hdd-network"></i> ' + i18n.t("Edit Source");
    document.getElementById("source-id").value = source.id;
    document.getElementById("source-name").value = source.name;
    document.getElementById("source-department-id").value = source.department_id;
    document.getElementById("source-access-method").value = source.access_method;
    document.getElementById("source-host").value = source.host;
    document.getElementById("source-port").value = source.port || "";
    document.getElementById("source-username").value = "";
    document.getElementById("source-password").value = "";
    document.getElementById("source-domain").value = source.domain || "";
    document.getElementById("source-encoding").value = source.encoding;
    document.getElementById("source-source-type").value = source.source_type;
    document.getElementById("source-collection-mode").value = source.collection_mode;
    document.getElementById("source-polling-interval").value = source.polling_interval_sec;
    document.getElementById("source-is-enabled").checked = source.is_enabled;
    document.getElementById("source-alert-on-change").checked = source.alert_on_change || false;
    document.getElementById("source-parser-pattern").value = source.parser_pattern || "";
    document.getElementById("source-severity-field").value = source.severity_field || "";
    document.getElementById("source-default-severity").value = source.default_severity;

    // Populate paths
    var container = document.getElementById("paths-container");
    container.innerHTML = "";
    if (source.paths && source.paths.length > 0) {
        for (var i = 0; i < source.paths.length; i++) {
            addPathRow(source.paths[i]);
        }
    } else {
        addPathRow();
    }

    toggleParserTab();
    updatePathHints();
    // Reset to Connection tab
    var firstTab = document.querySelector("#sourceModal .stl-tabs .nav-link");
    if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
    new bootstrap.Modal(document.getElementById("sourceModal")).show();
}

function resetSourceForm() {
    document.getElementById("source-id").value = "";
    document.getElementById("source-name").value = "";
    document.getElementById("source-department-id").value = "";
    document.getElementById("source-access-method").value = "ftp";
    document.getElementById("source-host").value = "";
    document.getElementById("source-port").value = "";
    document.getElementById("source-username").value = "";
    document.getElementById("source-password").value = "";
    document.getElementById("source-domain").value = "";
    document.getElementById("source-encoding").value = "utf-8";
    document.getElementById("source-source-type").value = "OTHER";
    document.getElementById("source-collection-mode").value = "metadata_only";
    document.getElementById("source-polling-interval").value = "60";
    document.getElementById("source-is-enabled").checked = true;
    document.getElementById("source-alert-on-change").checked = false;
    document.getElementById("source-parser-pattern").value = "";
    document.getElementById("source-severity-field").value = "";
    document.getElementById("source-default-severity").value = "INFO";

    // Reset paths: clear and add one empty row
    var container = document.getElementById("paths-container");
    container.innerHTML = "";
    addPathRow();
}

// ===== Path Row Management =====

function addPathRow(pathData) {
    var container = document.getElementById("paths-container");
    var row = document.createElement("div");
    row.className = "row g-1 mb-1 path-row align-items-end";

    var pathId = pathData && pathData.id ? pathData.id : "";
    var basePath = pathData ? pathData.base_path : "";
    var filePattern = pathData ? pathData.file_pattern : "*.log";
    var isEnabled = pathData ? pathData.is_enabled : true;

    var method = document.getElementById("source-access-method").value;
    var placeholder = method === "smb" ? "share_name/subfolder" : "/var/log/app";

    row.innerHTML = '<input type="hidden" class="path-id-input" value="' + pathId + '">'
        + '<div class="col-6">'
        + '<div class="stl-field">'
        + '<label class="stl-label"><i class="bi bi-folder2"></i> ' + i18n.t("Base Path") + "</label>"
        + '<input type="text" class="form-control form-control-sm font-monospace path-base-path" '
        + 'value="' + escapeHtml(basePath) + '" placeholder="' + placeholder + '" required>'
        + "</div></div>"
        + '<div class="col-3">'
        + '<div class="stl-field">'
        + '<label class="stl-label"><i class="bi bi-file-earmark-text"></i> ' + i18n.t("Pattern") + "</label>"
        + '<input type="text" class="form-control form-control-sm font-monospace path-file-pattern" '
        + 'value="' + escapeHtml(filePattern) + '">'
        + "</div></div>"
        + '<div class="col-2">'
        + '<div class="form-check form-switch ms-2 mb-1">'
        + '<input class="form-check-input path-enabled" type="checkbox"' + (isEnabled ? " checked" : "") + '>'
        + '<label class="form-check-label small">' + i18n.t("On") + "</label>"
        + "</div></div>"
        + '<div class="col-1 text-end">'
        + '<button type="button" class="btn btn-outline-danger btn-sm mb-1" onclick="removePathRow(this)" title="' + i18n.t("Remove") + '">'
        + '<i class="bi bi-x-lg"></i></button>'
        + "</div>";

    container.appendChild(row);
}

function removePathRow(btn) {
    var row = btn.closest(".path-row");
    var container = document.getElementById("paths-container");
    // Don't remove last row
    if (container.querySelectorAll(".path-row").length <= 1) {
        showToast(i18n.t("At least one path is required"), "warning");
        return;
    }
    row.remove();
}

function collectPaths() {
    var rows = document.querySelectorAll("#paths-container .path-row");
    var paths = [];
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var basePath = row.querySelector(".path-base-path").value.trim();
        if (!basePath) continue;
        var pathObj = {
            base_path: basePath,
            file_pattern: row.querySelector(".path-file-pattern").value.trim() || "*.log",
            is_enabled: row.querySelector(".path-enabled").checked,
        };
        var pathId = row.querySelector(".path-id-input").value;
        if (pathId) pathObj.id = parseInt(pathId);
        paths.push(pathObj);
    }
    return paths;
}

function updatePathHints() {
    var method = document.getElementById("source-access-method").value;
    var placeholder = method === "smb" ? "share_name/subfolder" : "/var/log/app";
    var inputs = document.querySelectorAll("#paths-container .path-base-path");
    for (var i = 0; i < inputs.length; i++) {
        inputs[i].placeholder = placeholder;
    }
}

function toggleParserTab() {
    var mode = document.getElementById("source-collection-mode").value;
    var parserNav = document.getElementById("src-tab-parser-nav");
    if (parserNav) {
        if (mode === "full_import") {
            parserNav.classList.remove("d-none");
        } else {
            parserNav.classList.add("d-none");
            // If parser tab is currently active, switch to Connection tab
            var parserTabBtn = parserNav.querySelector(".nav-link");
            if (parserTabBtn && parserTabBtn.classList.contains("active")) {
                var firstTab = document.querySelector("#sourceModal .stl-tabs .nav-link");
                if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
            }
        }
    }
}

async function saveSource() {
    var id = document.getElementById("source-id").value;
    var portVal = document.getElementById("source-port").value;
    var paths = collectPaths();

    if (paths.length === 0) {
        showToast(i18n.t("At least one path is required"), "warning");
        return;
    }

    var data = {
        name: document.getElementById("source-name").value,
        department_id: parseInt(document.getElementById("source-department-id").value),
        access_method: document.getElementById("source-access-method").value,
        host: document.getElementById("source-host").value,
        port: portVal ? parseInt(portVal) : null,
        username: document.getElementById("source-username").value,
        password: document.getElementById("source-password").value,
        domain: document.getElementById("source-domain").value || null,
        paths: paths,
        encoding: document.getElementById("source-encoding").value,
        source_type: document.getElementById("source-source-type").value,
        collection_mode: document.getElementById("source-collection-mode").value,
        polling_interval_sec: parseInt(document.getElementById("source-polling-interval").value),
        is_enabled: document.getElementById("source-is-enabled").checked,
        alert_on_change: document.getElementById("source-alert-on-change").checked,
        parser_pattern: document.getElementById("source-parser-pattern").value || null,
        severity_field: document.getElementById("source-severity-field").value || null,
        default_severity: document.getElementById("source-default-severity").value,
    };

    // For update, remove empty password/username (don't overwrite with empty string)
    if (id) {
        if (!data.username) delete data.username;
        if (!data.password) delete data.password;
    }

    try {
        if (id) {
            await api.put("/api/log-sources/" + id, data);
            showToast(i18n.t("Log source updated"), "success");
        } else {
            await api.post("/api/log-sources/", data);
            showToast(i18n.t("Log source created"), "success");
        }
        bootstrap.Modal.getInstance(document.getElementById("sourceModal")).hide();
        await loadSources();
    } catch (e) {
        showToast(e.message, "danger");
    }
}

async function deleteSource(id) {
    if (!confirm(i18n.t("Delete this log source?"))) return;
    try {
        await api.del("/api/log-sources/" + id);
        showToast(i18n.t("Log source deleted"), "success");
        await loadSources();
    } catch (e) {
        showToast(e.message, "danger");
    }
}

// ===== Test Connection =====

async function testConnection(id) {
    var body = document.getElementById("testResultBody");
    body.innerHTML = '<div class="text-center">'
        + '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>'
        + '<p class="mt-2 mb-0 text-muted small">' + i18n.t("Testing connection...") + "</p>"
        + "</div>";
    new bootstrap.Modal(document.getElementById("testResultModal")).show();

    try {
        var result = await api.post("/api/log-sources/" + id + "/test");
        var html = "";
        if (result.status === "ok") {
            html += '<div class="text-center mb-3">'
                + '<i class="bi bi-check-circle-fill text-success" style="font-size:2rem"></i>'
                + '<p class="mt-2 mb-0">' + escapeHtml(result.message) + "</p>"
                + "</div>";
        } else {
            html += '<div class="text-center mb-3">'
                + '<i class="bi bi-x-circle-fill text-danger" style="font-size:2rem"></i>'
                + '<p class="mt-2 mb-0 text-danger">' + escapeHtml(result.message) + "</p>"
                + "</div>";
        }

        // Show per-path results if available
        if (result.path_results && result.path_results.length > 0) {
            html += '<table class="table table-sm table-bordered mb-0">'
                + "<thead><tr>"
                + "<th>" + i18n.t("Base Path") + "</th>"
                + "<th>" + i18n.t("Pattern") + "</th>"
                + "<th>" + i18n.t("Status") + "</th>"
                + "<th>" + i18n.t("Files") + "</th>"
                + "</tr></thead><tbody>";
            for (var i = 0; i < result.path_results.length; i++) {
                var pr = result.path_results[i];
                var statusBadge = pr.status === "ok"
                    ? '<span class="badge bg-success">OK</span>'
                    : '<span class="badge bg-danger">' + i18n.t("Error") + "</span>";
                html += "<tr" + (pr.status !== "ok" ? ' class="table-danger"' : "") + ">"
                    + '<td class="font-monospace small">' + escapeHtml(pr.base_path) + "</td>"
                    + '<td class="small">' + escapeHtml(pr.file_pattern) + "</td>"
                    + "<td>" + statusBadge + "</td>"
                    + "<td>" + pr.file_count + "</td>"
                    + "</tr>";
                if (pr.status !== "ok") {
                    html += '<tr class="table-danger"><td colspan="4" class="small text-danger">'
                        + escapeHtml(pr.message) + "</td></tr>";
                }
            }
            html += "</tbody></table>";
        }
        body.innerHTML = html;
    } catch (e) {
        body.innerHTML = '<div class="text-center">'
            + '<i class="bi bi-x-circle-fill text-danger" style="font-size:2rem"></i>'
            + '<p class="mt-2 mb-0 text-danger">' + escapeHtml(e.message) + "</p>"
            + "</div>";
    }
}

// ===== Scan Source =====

async function scanSource(id) {
    var source = sources.find(function (s) { return s.id === id; });
    var title = source ? escapeHtml(source.name) : "#" + id;
    var body = document.getElementById("testResultBody");
    body.innerHTML = '<div class="text-center">'
        + '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>'
        + '<p class="mt-2 mb-0 text-muted small">' + i18n.t("Scanning...") + "</p>"
        + "</div>";
    document.querySelector("#testResultModal .modal-title").innerHTML =
        '<i class="bi bi-arrow-repeat"></i> ' + i18n.t("Scan") + " - " + title;
    new bootstrap.Modal(document.getElementById("testResultModal")).show();

    try {
        var result = await api.post("/api/log-sources/" + id + "/scan");
        var html = '<div class="text-center mb-3">';
        if (result.new_count > 0 || result.updated_count > 0) {
            html += '<i class="bi bi-check-circle-fill text-warning" style="font-size:2rem"></i>';
        } else {
            html += '<i class="bi bi-check-circle-fill text-success" style="font-size:2rem"></i>';
        }
        html += '<p class="mt-2 mb-0">' + escapeHtml(result.message) + "</p>";
        if (result.alerts_created > 0) {
            html += '<p class="mt-1 mb-0"><span class="badge bg-warning text-dark">'
                + i18n.t("Alert created") + "</span></p>";
        }
        html += "</div>";

        // Show changed paths with folder links
        if (result.changed_paths && result.changed_paths.length > 0) {
            html += '<div class="border-top pt-2">';
            for (var ci = 0; ci < result.changed_paths.length; ci++) {
                var cp = result.changed_paths[ci];
                var scanCopyPath = cp.copy_path || cp.folder_link;
                html += '<div class="mb-2">'
                    + '<span class="text-decoration-none font-monospace small copy-path-btn" role="button" '
                    + 'data-copy-path="' + escapeHtml(scanCopyPath) + '" title="' + i18n.t("Click to copy path") + '">'
                    + '<i class="bi bi-folder2-open"></i> ' + escapeHtml(cp.base_path)
                    + ' <i class="bi bi-clipboard ms-1 text-muted small"></i>'
                    + '</span>';
                if (cp.new_files && cp.new_files.length > 0) {
                    html += '<div class="ms-3"><span class="badge bg-primary me-1">' + i18n.t("New") + '</span>'
                        + '<small>' + cp.new_files.map(escapeHtml).join(", ") + '</small></div>';
                }
                if (cp.updated_files && cp.updated_files.length > 0) {
                    html += '<div class="ms-3"><span class="badge bg-warning text-dark me-1">' + i18n.t("Updated") + '</span>'
                        + '<small>' + cp.updated_files.map(escapeHtml).join(", ") + '</small></div>';
                }
                html += '</div>';
            }
            html += '</div>';
        }

        body.innerHTML = html;
        await loadSources();
    } catch (e) {
        body.innerHTML = '<div class="text-center">'
            + '<i class="bi bi-x-circle-fill text-danger" style="font-size:2rem"></i>'
            + '<p class="mt-2 mb-0 text-danger">' + escapeHtml(e.message) + "</p>"
            + "</div>";
    }
}

// ===== View Files =====

async function viewFiles(id) {
    var source = sources.find(function (s) { return s.id === id; });
    var title = source ? escapeHtml(source.name) : "#" + id;
    document.getElementById("filesModalTitle").innerHTML =
        '<i class="bi bi-files"></i> ' + title + " - " + i18n.t("Files");

    var tbody = document.getElementById("files-tbody");
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">'
        + '<div class="spinner-border spinner-border-sm" role="status"></div> '
        + i18n.t("Loading...") + "</td></tr>";

    new bootstrap.Modal(document.getElementById("filesModal")).show();

    try {
        var files = await api.get("/api/log-sources/" + id + "/files");
        renderFileTable(files);
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger py-3">'
            + escapeHtml(e.message) + "</td></tr>";
    }
}

function renderFileTable(files) {
    var tbody = document.getElementById("files-tbody");

    if (!files || files.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">'
            + i18n.t("No files found") + "</td></tr>";
        return;
    }

    tbody.innerHTML = files.map(function (f) {
        var statusBadge = fileStatusBadge(f.status);
        var modifiedAt = f.file_modified_at
            ? new Date(f.file_modified_at).toLocaleString()
            : "-";

        return "<tr>"
            + '<td><i class="bi bi-file-text text-muted"></i> '
            + '<span class="font-monospace small">' + escapeHtml(f.file_name) + "</span></td>"
            + '<td class="text-end"><small>' + formatFileSize(f.file_size) + "</small></td>"
            + "<td><small>" + escapeHtml(modifiedAt) + "</small></td>"
            + "<td>" + statusBadge + "</td>"
            + '<td class="text-end"><small>' + f.last_read_line + "</small></td>"
            + "</tr>";
    }).join("");
}

function fileStatusBadge(status) {
    switch (status) {
        case "new":
            return '<span class="badge bg-primary">' + i18n.t("New") + "</span>";
        case "unchanged":
            return '<span class="badge bg-secondary">' + i18n.t("Unchanged") + "</span>";
        case "updated":
            return '<span class="badge bg-warning text-dark">' + i18n.t("Updated") + "</span>";
        case "deleted":
            return '<span class="badge bg-danger">' + i18n.t("Deleted") + "</span>";
        case "error":
            return '<span class="badge bg-danger">' + i18n.t("Error") + "</span>";
        default:
            return '<span class="badge bg-secondary">' + escapeHtml(status) + "</span>";
    }
}

// ===== Utilities =====

function formatFileSize(bytes) {
    if (bytes === 0 || bytes === null || bytes === undefined) return "0 B";
    var units = ["B", "KB", "MB", "GB", "TB"];
    var i = 0;
    var size = bytes;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    if (i === 0) return size + " " + units[i];
    return size.toFixed(1) + " " + units[i];
}

function truncateText(text, maxLen) {
    if (!text) return "";
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen) + "...";
}

// ===== Real-time Log Stream =====

async function loadLogs() {
    try {
        allLogs = await api.get("/api/logs/?limit=100");
    } catch (e) {
        allLogs = [];
    }
    renderLogs();
}

function renderLogs() {
    var filtered = allLogs;
    if (currentFilter === "important") {
        filtered = allLogs.filter(function (l) {
            return ["WARNING", "ERROR", "CRITICAL"].indexOf(l.severity) !== -1;
        });
    }

    var tbody = document.getElementById("log-list");
    if (!tbody) return;

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">'
            + i18n.t("No logs") + "</td></tr>";
        return;
    }

    tbody.innerHTML = filtered.map(function (l) {
        return '<tr class="log-row-' + l.severity + '">'
            + "<td><small>" + new Date(l.received_at).toLocaleString() + "</small></td>"
            + '<td><span class="badge bg-' + severityColor(l.severity) + '">' + l.severity + "</span></td>"
            + "<td><small>" + escapeHtml(l.system_name) + "</small></td>"
            + "<td><small>" + escapeHtml(l.log_type) + "</small></td>"
            + "<td>" + escapeHtml(l.message) + "</td>"
            + "</tr>";
    }).join("");
}

function filterLogs(filter, btn) {
    currentFilter = filter;
    var buttons = btn.parentElement.querySelectorAll(".btn");
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].classList.remove("active");
    }
    btn.classList.add("active");
    renderLogs();
}

function connectWebSocket() {
    var protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(protocol + "//" + location.host + "/ws/logs");
    var statusEl = document.getElementById("ws-status");

    ws.onopen = function () {
        if (statusEl) {
            statusEl.textContent = i18n.t("Connected");
            statusEl.className = "badge bg-success me-2";
        }
    };

    ws.onclose = function () {
        if (statusEl) {
            statusEl.textContent = i18n.t("Disconnected");
            statusEl.className = "badge bg-danger me-2";
        }
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = function () {
        ws.close();
    };

    ws.onmessage = function (event) {
        var log = JSON.parse(event.data);
        allLogs.unshift(log);
        if (allLogs.length > 200) allLogs.pop();
        renderLogs();
    };
}

function severityColor(s) {
    switch (s) {
        case "ERROR":
        case "CRITICAL":
            return "danger";
        case "WARNING":
            return "warning";
        case "DEBUG":
            return "secondary";
        default:
            return "info";
    }
}

// ===== Clipboard copy for folder paths =====

document.addEventListener("click", function (e) {
    var btn = e.target.closest(".copy-path-btn");
    if (!btn) return;
    var path = btn.getAttribute("data-copy-path");
    if (!path) return;
    navigator.clipboard.writeText(path).then(function () {
        showToast(i18n.t("Path copied"), "success");
    }).catch(function () {
        showToast(i18n.t("Copy failed"), "danger");
    });
});

// ===== Bootstrap =====

init();
