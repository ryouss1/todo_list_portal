let clockedIn = false;
let currentAttendance = null;
let elapsedTimer = null;

// Button label configurations per activity type
const LABELS = {
    work:    { in: "Clock In",  out: "Clock Out" },
    break:   { in: "休憩開始",   out: "休憩終了" },
    out:     { in: "外出",      out: "戻り" },
    meeting: { in: "会議開始",   out: "会議終了" },
};

async function loadStatus() {
    try {
        const data = await api.get("/api/attendances/status");
        clockedIn = data.is_clocked_in;
        currentAttendance = data.current_attendance;
        updateUI();
    } catch (e) {
        console.error("[attendance] loadStatus error:", e);
        showToast(e.message || i18n.t("Failed to load status"), "danger");
    }
    // Always load history regardless of status result
    loadHistory();
}

function updateUI() {
    const statusEl = document.getElementById("clock-status");
    const timeEl = document.getElementById("clock-time");
    const btnIn = document.getElementById("btn-clock-in");
    const btnOut = document.getElementById("btn-clock-out");
    const activity = document.getElementById("activity-type").value;

    if (clockedIn && currentAttendance) {
        statusEl.innerHTML = `<span class="text-success"><i class="bi bi-circle-fill"></i> ${i18n.t('Clocked In')}</span>`;
        if (activity === "work") {
            btnIn.disabled = true;
            btnOut.disabled = false;
        } else {
            btnIn.disabled = false;
            btnOut.disabled = false;
        }
        startElapsedTimer();
    } else {
        statusEl.innerHTML = `<span class="text-secondary"><i class="bi bi-circle"></i> ${i18n.t('Not Clocked In')}</span>`;
        timeEl.textContent = "";
        if (activity === "work") {
            btnIn.disabled = false;
            btnOut.disabled = true;
        } else {
            btnIn.disabled = true;
            btnOut.disabled = true;
        }
        if (elapsedTimer) {
            clearInterval(elapsedTimer);
            elapsedTimer = null;
        }
    }
}

function onActivityChange() {
    const activity = document.getElementById("activity-type").value;
    const labels = LABELS[activity];
    document.getElementById("label-clock-in").textContent = i18n.t(labels.in);
    document.getElementById("label-clock-out").textContent = i18n.t(labels.out);
    updateUI();
}

function onRemoteChange() {
    // No-op for now; remote flag is read at action time
}

function startElapsedTimer() {
    if (elapsedTimer) clearInterval(elapsedTimer);
    const start = new Date(currentAttendance.clock_in).getTime();
    function tick() {
        const elapsed = Math.floor((Date.now() - start) / 1000);
        const h = Math.floor(elapsed / 3600);
        const m = Math.floor((elapsed % 3600) / 60);
        const s = elapsed % 60;
        document.getElementById("clock-time").textContent =
            `${i18n.t('Elapsed')}: ${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }
    tick();
    elapsedTimer = setInterval(tick, 1000);
}

function getCurrentTimeHHMM() {
    const now = new Date();
    return String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0");
}

async function updatePresence(status) {
    try {
        await api.put("/api/presence/status", { status });
    } catch (e) {
        showToast(i18n.t("Presence update failed: {error}", {error: e.message || i18n.t("Unknown error")}), "warning");
    }
}

function getReturnPresence() {
    return document.getElementById("remote-check").checked ? "remote" : "available";
}

async function handleAction(direction) {
    const activity = document.getElementById("activity-type").value;
    const isRemote = document.getElementById("remote-check").checked;
    const note = document.getElementById("attendance-note").value || null;

    try {
        if (activity === "work") {
            if (direction === "in") {
                await api.post("/api/attendances/clock-in", { note });
                await updatePresence(isRemote ? "remote" : "available");
                showToast(i18n.t("Clock In completed"), "success");
            } else {
                await api.post("/api/attendances/clock-out", { note });
                await updatePresence("offline");
                showToast(i18n.t("Clock Out completed"), "success");
            }
            document.getElementById("attendance-note").value = "";
        } else if (activity === "break") {
            if (!currentAttendance) {
                showToast(i18n.t("Clock In first before starting break"), "warning");
                return;
            }
            if (direction === "in") {
                await api.post(`/api/attendances/${currentAttendance.id}/break-start`);
                await updatePresence("break");
                showToast(i18n.t("休憩開始"), "success");
            } else {
                await api.post(`/api/attendances/${currentAttendance.id}/break-end`);
                await updatePresence(getReturnPresence());
                showToast(i18n.t("休憩終了"), "success");
            }
        } else if (activity === "out") {
            if (!clockedIn) {
                showToast(i18n.t("Clock In first before going out"), "warning");
                return;
            }
            if (direction === "in") {
                await updatePresence("out");
                showToast(i18n.t("外出しました"), "success");
            } else {
                await updatePresence(getReturnPresence());
                showToast(i18n.t("戻りました"), "success");
            }
        } else if (activity === "meeting") {
            if (!clockedIn) {
                showToast(i18n.t("Clock In first before starting a meeting"), "warning");
                return;
            }
            if (direction === "in") {
                await updatePresence("meeting");
                showToast(i18n.t("会議開始"), "success");
            } else {
                await updatePresence(getReturnPresence());
                showToast(i18n.t("会議終了"), "success");
            }
        }
        loadStatus();
    } catch (e) {
        showToast(e.message || i18n.t("Action failed"), "danger");
    }
}

function formatTimeLocal(dtStr) {
    if (!dtStr) return null;
    return new Date(dtStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatTimeHHMM(dtStr) {
    if (!dtStr) return "";
    const d = new Date(dtStr);
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
}

function calcDuration(a) {
    const cin = new Date(a.clock_in);
    const cout = a.clock_out ? new Date(a.clock_out) : null;
    if (!cout) return "-";
    let secs = Math.floor((cout - cin) / 1000);
    // Subtract all breaks
    if (a.breaks && a.breaks.length > 0) {
        for (const brk of a.breaks) {
            if (brk.break_start && brk.break_end) {
                const bs = new Date(brk.break_start);
                const be = new Date(brk.break_end);
                secs -= Math.floor((be - bs) / 1000);
            }
        }
    }
    if (secs < 0) secs = 0;
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${h}h ${m}m`;
}

function formatBreaks(breaks) {
    if (!breaks || breaks.length === 0) return "-";
    return breaks.map((brk) => {
        const start = formatTimeLocal(brk.break_start);
        if (brk.break_end) {
            return `${start} - ${formatTimeLocal(brk.break_end)}`;
        }
        return `${start} - <span class="badge bg-warning text-dark">${i18n.t('On Break')}</span>`;
    }).join("<br>");
}

function currentMonthStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function searchByMonth() {
    loadHistory();
}

function downloadExcel() {
    const monthVal = document.getElementById("filter-month").value;
    if (!monthVal) return;
    const [y, m] = monthVal.split("-");
    window.location.href = `/api/attendances/export?year=${y}&month=${m}`;
}

async function loadHistory() {
    try {
        const monthVal = document.getElementById("filter-month").value;
        let url = "/api/attendances/";
        if (monthVal) {
            const [y, m] = monthVal.split("-");
            url += `?year=${y}&month=${m}`;
        }
        const list = await api.get(url);
        const tbody = document.getElementById("attendance-list");
        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-muted text-center">${i18n.t('No records')}</td></tr>`;
            return;
        }
        tbody.innerHTML = list
            .map((a) => {
                const cin = formatTimeLocal(a.clock_in);
                const cout = a.clock_out ? formatTimeLocal(a.clock_out) : `<span class="badge bg-success">${i18n.t('Active')}</span>`;
                const breakStr = formatBreaks(a.breaks);
                const duration = calcDuration(a);
                const inputType = a.input_type || "web";
                const inputBadge = { web: "WEB", ic_card: "IC", admin: i18n.t("管理者") }[inputType] || inputType;
                const inputClass = { web: "bg-secondary", ic_card: "bg-info", admin: "bg-danger" }[inputType] || "bg-secondary";
                const isLocked = inputType === "admin";
                return `<tr>
                <td>${a.date}</td>
                <td>${cin}</td>
                <td>${cout}</td>
                <td>${breakStr}</td>
                <td>${duration}</td>
                <td><span class="badge ${inputClass}">${inputBadge}</span></td>
                <td>${a.note ? escapeHtml(a.note) : ""}</td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary me-1" onclick="openEdit(${a.id})" ${isLocked ? "disabled" : ""}>
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="openDelete(${a.id})" ${isLocked ? "disabled" : ""}>
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
            })
            .join("");
    } catch (e) {
        showToast(e.message || i18n.t("Failed to load history"), "danger");
    }
}

function addBreakRow(startVal, endVal) {
    const container = document.getElementById("edit-breaks");
    if (container.querySelectorAll(".break-row").length >= 3) {
        showToast(i18n.t("最大3件までです"), "warning");
        return;
    }
    const row = document.createElement("div");
    row.className = "d-flex gap-2 mb-1 break-row";
    row.innerHTML = `
        <input type="time" class="form-control form-control-sm edit-break-start" value="${startVal || ""}">
        <span class="align-self-center">-</span>
        <input type="time" class="form-control form-control-sm edit-break-end" value="${endVal || ""}">
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.break-row').remove()">\u00d7</button>
    `;
    container.appendChild(row);
}

async function openEdit(id) {
    try {
        const data = await api.get(`/api/attendances/${id}`);
        document.getElementById("edit-id").value = data.id;
        document.getElementById("edit-clock-in").value = formatTimeHHMM(data.clock_in);
        document.getElementById("edit-clock-out").value = formatTimeHHMM(data.clock_out);
        document.getElementById("edit-note").value = data.note || "";
        const breaksContainer = document.getElementById("edit-breaks");
        breaksContainer.innerHTML = "";
        if (data.breaks) {
            data.breaks.forEach(brk => addBreakRow(
                formatTimeHHMM(brk.break_start),
                formatTimeHHMM(brk.break_end)
            ));
        }
        new bootstrap.Modal(document.getElementById("editModal")).show();
    } catch (e) {
        showToast(e.message || i18n.t("Failed to load record"), "danger");
    }
}

async function updateAttendance() {
    try {
        const id = document.getElementById("edit-id").value;
        const payload = {};
        const clockIn = document.getElementById("edit-clock-in").value;
        const clockOut = document.getElementById("edit-clock-out").value;
        const note = document.getElementById("edit-note").value;

        if (clockIn) payload.clock_in = clockIn;
        if (clockOut) payload.clock_out = clockOut;
        if (note) payload.note = note;

        const breakRows = document.querySelectorAll("#edit-breaks .break-row");
        const breaks = [];
        breakRows.forEach(row => {
            const start = row.querySelector(".edit-break-start").value;
            const end = row.querySelector(".edit-break-end").value;
            if (start) breaks.push({ start, end: end || null });
        });
        payload.breaks = breaks;

        await api.put(`/api/attendances/${id}`, payload);
        bootstrap.Modal.getInstance(document.getElementById("editModal")).hide();
        showToast(i18n.t("Attendance record updated"), "success");
        loadHistory();
    } catch (e) {
        showToast(e.message || i18n.t("Failed to update record"), "danger");
    }
}

function openDelete(id) {
    document.getElementById("delete-id").value = id;
    new bootstrap.Modal(document.getElementById("deleteModal")).show();
}

async function deleteAttendance() {
    try {
        const id = document.getElementById("delete-id").value;
        await api.del(`/api/attendances/${id}`);
        bootstrap.Modal.getInstance(document.getElementById("deleteModal")).hide();
        showToast(i18n.t("Attendance record deleted"), "success");
        loadStatus();
    } catch (e) {
        showToast(e.message || i18n.t("Failed to delete record"), "danger");
    }
}

// ---- Manual Create ----

function todayStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function openCreate() {
    document.getElementById("create-date").value = todayStr();
    document.getElementById("create-clock-in").value = "";
    document.getElementById("create-clock-out").value = "";
    document.getElementById("create-note").value = "";
    document.getElementById("create-breaks").innerHTML = "";
    renderCreatePresetButtons();
    new bootstrap.Modal(document.getElementById("createModal")).show();
}

function renderCreatePresetButtons() {
    const container = document.getElementById("create-preset-buttons");
    if (presets.length === 0) {
        container.innerHTML = `<span class="text-muted small">${i18n.t('プリセットなし')}</span>`;
        return;
    }
    container.innerHTML = presets.map(p => {
        let label = `${p.clock_in}-${p.clock_out}`;
        return `<button type="button" class="btn btn-sm btn-outline-primary" onclick="fillFromPreset(${p.id})">
            <i class="bi bi-clock"></i> ${escapeHtml(p.name)}
        </button>`;
    }).join("");
}

function fillFromPreset(presetId) {
    const p = presets.find(x => x.id === presetId);
    if (!p) return;
    document.getElementById("create-clock-in").value = p.clock_in;
    document.getElementById("create-clock-out").value = p.clock_out;
    // Replace breaks with preset break
    document.getElementById("create-breaks").innerHTML = "";
    if (p.break_start) {
        addCreateBreakRow(p.break_start, p.break_end || "");
    }
}

function addCreateBreakRow(startVal, endVal) {
    const container = document.getElementById("create-breaks");
    if (container.querySelectorAll(".break-row").length >= 3) {
        showToast(i18n.t("最大3件までです"), "warning");
        return;
    }
    const row = document.createElement("div");
    row.className = "d-flex gap-2 mb-1 break-row";
    row.innerHTML = `
        <input type="time" class="form-control form-control-sm create-break-start" value="${startVal || ""}">
        <span class="align-self-center">-</span>
        <input type="time" class="form-control form-control-sm create-break-end" value="${endVal || ""}">
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.break-row').remove()">\u00d7</button>
    `;
    container.appendChild(row);
}

async function createAttendance() {
    try {
        const dateVal = document.getElementById("create-date").value;
        const clockIn = document.getElementById("create-clock-in").value;
        if (!dateVal || !clockIn) {
            showToast(i18n.t("日付とClock Inは必須です"), "warning");
            return;
        }
        const payload = { date: dateVal, clock_in: clockIn };
        const clockOut = document.getElementById("create-clock-out").value;
        if (clockOut) payload.clock_out = clockOut;
        const note = document.getElementById("create-note").value;
        if (note) payload.note = note;

        const breakRows = document.querySelectorAll("#create-breaks .break-row");
        const breaks = [];
        breakRows.forEach(row => {
            const start = row.querySelector(".create-break-start").value;
            const end = row.querySelector(".create-break-end").value;
            if (start) breaks.push({ start, end: end || null });
        });
        if (breaks.length > 0) payload.breaks = breaks;

        await api.post("/api/attendances/", payload);
        bootstrap.Modal.getInstance(document.getElementById("createModal")).hide();
        showToast(i18n.t("勤怠を登録しました"), "success");
        loadStatus();
    } catch (e) {
        showToast(e.message || i18n.t("登録に失敗しました"), "danger");
    }
}

// ---- Preset / Default Set ----

let presets = [];
let userPresetId = null;

async function loadPresets() {
    try {
        const [presetList, userPref] = await Promise.all([
            api.get("/api/attendance-presets/"),
            api.get("/api/attendances/my-preset"),
        ]);
        presets = presetList;
        userPresetId = userPref.default_preset_id || (presets.length > 0 ? presets[0].id : null);
        updateDefaultSetPreview();
    } catch (e) {
        console.error("[attendance] loadPresets error:", e);
    }
}

function updateDefaultSetPreview() {
    const el = document.getElementById("default-set-preview");
    if (!el) return;
    const preset = presets.find((p) => p.id === userPresetId);
    if (preset) {
        let text = `${preset.clock_in} - ${preset.clock_out}`;
        if (preset.break_start && preset.break_end) {
            text += ` / ${i18n.t('休憩')} ${preset.break_start} - ${preset.break_end}`;
        }
        el.textContent = i18n.t('適用されるプリセット: {text}', {text});
    } else {
        el.textContent = "";
    }
}

async function defaultSet() {
    try {
        await api.post("/api/attendances/default-set");
        bootstrap.Modal.getInstance(document.getElementById("defaultSetConfirmModal")).hide();
        const preset = presets.find((p) => p.id === userPresetId);
        const name = preset ? preset.name : "default";
        showToast(i18n.t("Default Set 完了 ({name})", {name}), "success");
        loadStatus();
    } catch (e) {
        showToast(e.message || i18n.t("Failed to set default attendance"), "danger");
    }
}

function openPresetModal() {
    const container = document.getElementById("preset-list");
    if (presets.length === 0) {
        container.innerHTML = `<p class="text-muted">${i18n.t('No presets available')}</p>`;
        return;
    }
    container.innerHTML = presets
        .map((p) => {
            const checked = p.id === userPresetId ? "checked" : "";
            let desc = `${p.clock_in} - ${p.clock_out}`;
            if (p.break_start && p.break_end) {
                desc += ` / ${i18n.t('休憩')} ${p.break_start} - ${p.break_end}`;
            }
            return `<div class="form-check mb-2">
                <input class="form-check-input" type="radio" name="preset" id="preset-${p.id}" value="${p.id}" ${checked}>
                <label class="form-check-label" for="preset-${p.id}">
                    <strong>${escapeHtml(p.name)}</strong><br>
                    <small class="text-muted">${desc}</small>
                </label>
            </div>`;
        })
        .join("");
}

async function savePreset() {
    const selected = document.querySelector('input[name="preset"]:checked');
    if (!selected) {
        showToast(i18n.t("プリセットを選択してください"), "warning");
        return;
    }
    try {
        const presetId = parseInt(selected.value, 10);
        await api.put("/api/attendances/my-preset", { default_preset_id: presetId });
        userPresetId = presetId;
        updateDefaultSetPreview();
        bootstrap.Modal.getInstance(document.getElementById("presetModal")).hide();
        const preset = presets.find((p) => p.id === presetId);
        showToast(i18n.t("デフォルトを「{name}」に変更しました", {name: preset ? preset.name : presetId}), "success");
    } catch (e) {
        showToast(e.message || i18n.t("Failed to save preset"), "danger");
    }
}

function fillEditBreakFromPreset() {
    const preset = presets.find(p => p.id === userPresetId) || (presets.length > 0 ? presets[0] : null);
    if (!preset) {
        showToast(i18n.t("プリセットがありません"), "warning");
        return;
    }
    if (!preset.break_start) {
        showToast(i18n.t("プリセットに休憩が設定されていません"), "warning");
        return;
    }
    const container = document.getElementById("edit-breaks");
    container.innerHTML = "";
    addBreakRow(preset.break_start, preset.break_end || "");
}

// Render preset options when modal opens
document.getElementById("presetModal").addEventListener("show.bs.modal", openPresetModal);

document.getElementById("filter-month").value = currentMonthStr();
loadStatus();
loadPresets();
