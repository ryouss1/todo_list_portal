let calendar = null;
let currentUserId = null;
let allUsers = {};
let userColors = {};
let settings = {};
let selectedUserIds = new Set();
let allRooms = [];

async function init() {
    const [me, users, settingsData, rooms] = await Promise.all([
        api.get('/api/auth/me'),
        api.get('/api/users/'),
        api.get('/api/calendar/settings'),
        api.get('/api/calendar/rooms'),
    ]);
    currentUserId = me.user_id;
    settings = settingsData;
    allRooms = rooms;

    users.forEach(u => {
        allUsers[u.id] = u.display_name || u.email;
        selectedUserIds.add(u.id);
    });

    buildUserFilters(users);
    buildAttendeeOptions(users);
    buildRoomOptions(rooms);
    initCalendar();
    connectCalendarWebSocket();
    requestNotificationPermission();
}

function buildRoomOptions(rooms) {
    const sel = document.getElementById('evt-room');
    rooms.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.name + (r.capacity ? ` (${r.capacity}名)` : '');
        sel.appendChild(opt);
    });
}

function toggleLocationType() {
    const isRoom = document.getElementById('loc-type-room').checked;
    document.getElementById('evt-room').classList.toggle('d-none', !isRoom);
    document.getElementById('evt-location').classList.toggle('d-none', isRoom);
}

function buildUserFilters(users) {
    const container = document.getElementById('user-filters');
    const defaultColors = [
        '#3788d8','#e74c3c','#2ecc71','#f39c12','#9b59b6',
        '#1abc9c','#e67e22','#3498db','#e91e63','#00bcd4','#ff9800','#8bc34a'
    ];
    users.forEach((u, i) => {
        const color = (u.id === currentUserId && settings.default_color)
            ? settings.default_color
            : defaultColors[i % defaultColors.length];
        userColors[u.id] = color;

        const label = document.createElement('label');
        label.className = 'user-filter-item';
        const isSelf = u.id === currentUserId;
        label.innerHTML = `
            <input type="checkbox" data-user-id="${u.id}" checked onchange="toggleUser(${u.id}, this.checked)">
            <span class="user-color-dot" style="background:${color}"></span>
            ${escapeHtml(allUsers[u.id])}${isSelf ? ' (me)' : ''}
        `;
        container.appendChild(label);
    });
}

function buildAttendeeOptions(users) {
    const sel = document.getElementById('evt-attendees');
    users.forEach(u => {
        if (u.id === currentUserId) return;
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = allUsers[u.id];
        sel.appendChild(opt);
    });
}

function toggleUser(userId, checked) {
    if (checked) selectedUserIds.add(userId);
    else selectedUserIds.delete(userId);
    reloadEvents();
}

function reloadEvents() {
    if (calendar) calendar.refetchEvents();
}

function initCalendar() {
    const calEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calEl, {
        initialView: settings.default_view || 'dayGridMonth',
        locale: 'ja',
        headerToolbar: {
            left: 'prev,today,next',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
        },
        buttonText: {
            today: 'Today',
            month: 'Month',
            week: 'Week',
            day: 'Day',
            list: 'List'
        },
        height: '100%',
        dayMaxEvents: 3,
        nowIndicator: true,
        selectable: true,
        editable: true,
        eventStartEditable: true,
        eventDurationEditable: true,
        slotMinTime: settings.working_hours_start ? settings.working_hours_start + ':00' : '07:00:00',
        slotMaxTime: '21:00:00',
        businessHours: {
            daysOfWeek: [1, 2, 3, 4, 5],
            startTime: settings.working_hours_start || '09:00',
            endTime: settings.working_hours_end || '18:00',
        },

        events: function(info, successCallback, failureCallback) {
            fetchEvents(info.start, info.end).then(events => {
                events.forEach(e => {
                    const loc = e.extendedProps?.location;
                    if (loc) {
                        e.extendedProps.original_title = e.title;
                        e.title = e.title + ' : ' + loc;
                    }
                });
                successCallback(events);
            }).catch(failureCallback);
        },

        select: function(info) {
            openCreateModal(info.start, info.end, info.allDay);
        },

        eventClick: function(info) {
            const props = info.event.extendedProps;
            if (props.read_only) {
                showToast('This is a linked event (read-only)', 'info');
                return;
            }
            openEditModal(info.event);
        },

        eventDrop: function(info) {
            handleEventMove(info);
        },

        eventResize: function(info) {
            handleEventMove(info);
        },

        eventDidMount: function(info) {
            const props = info.event.extendedProps;
            if (props.source_type) {
                info.el.setAttribute('data-source', props.source_type);
            }
            if (props.visibility === 'private' && props.creator_id !== currentUserId) {
                info.el.setAttribute('data-private', 'true');
            }
            // Tooltip
            const parts = [];
            if (props.creator_name) parts.push(props.creator_name);
            if (props.location) parts.push(props.location);
            if (props.description) parts.push(props.description);
            if (parts.length) {
                info.el.title = parts.join(' | ');
            }
        },
    });
    calendar.render();
}

async function fetchEvents(start, end) {
    const params = new URLSearchParams({
        start: start.toISOString(),
        end: end.toISOString(),
        include_source: 'true',
    });
    if (selectedUserIds.size > 0) {
        params.set('user_ids', Array.from(selectedUserIds).join(','));
    }
    return api.get(`/api/calendar/events?${params.toString()}`);
}

// --- Create / Edit ---

function openCreateModal(start, end, allDay) {
    document.getElementById('evt-id').value = '';
    document.getElementById('eventModalTitle').textContent = 'New Event';
    document.getElementById('evt-title').value = '';
    document.getElementById('evt-type').value = 'event';
    document.getElementById('evt-description').value = '';
    document.getElementById('evt-room').value = '';
    document.getElementById('evt-location').value = '';
    document.getElementById('loc-type-room').checked = true;
    toggleLocationType();
    document.getElementById('evt-visibility').value = 'public';
    document.getElementById('evt-recurrence').value = '';
    document.getElementById('recurrence-end-group').classList.add('d-none');
    document.getElementById('evt-recurrence-end').value = '';
    document.getElementById('evt-color-default').checked = true;
    document.getElementById('evt-color').value = userColors[currentUserId] || '#3788d8';
    document.getElementById('evt-color').disabled = true;
    document.getElementById('evt-delete-btn').classList.add('d-none');

    // Reset attendees
    const attSel = document.getElementById('evt-attendees');
    Array.from(attSel.options).forEach(o => o.selected = false);

    // Set reminder to default
    const reminderVal = settings.default_reminder_minutes || 10;
    const reminderSel = document.getElementById('evt-reminder');
    reminderSel.value = String(reminderVal);

    if (start) {
        const isAllDay = allDay || false;
        document.getElementById('evt-allday').checked = isAllDay;
        toggleAllDay();

        const startDate = formatDateInput(start);
        document.getElementById('evt-start-date').value = startDate;

        if (!isAllDay) {
            document.getElementById('evt-start-time').value = formatTimeInput(start);
            if (end) {
                document.getElementById('evt-end-date').value = formatDateInput(end);
                document.getElementById('evt-end-time').value = formatTimeInput(end);
            } else {
                document.getElementById('evt-end-date').value = startDate;
                document.getElementById('evt-end-time').value = formatTimeInput(new Date(start.getTime() + 3600000));
            }
        } else {
            document.getElementById('evt-end-date').value = end
                ? formatDateInput(new Date(end.getTime() - 86400000))
                : startDate;
        }
    } else {
        const now = new Date();
        document.getElementById('evt-allday').checked = false;
        toggleAllDay();
        document.getElementById('evt-start-date').value = formatDateInput(now);
        document.getElementById('evt-start-time').value = formatTimeInput(now);
        document.getElementById('evt-end-date').value = formatDateInput(now);
        document.getElementById('evt-end-time').value = formatTimeInput(new Date(now.getTime() + 3600000));
    }

    new bootstrap.Modal(document.getElementById('eventModal')).show();
    setTimeout(() => document.getElementById('evt-title').focus(), 300);
}

function openEditModal(fcEvent) {
    const props = fcEvent.extendedProps;
    document.getElementById('evt-id').value = fcEvent.id;
    document.getElementById('eventModalTitle').textContent = 'Edit Event';
    document.getElementById('evt-title').value = props.original_title || fcEvent.title;
    document.getElementById('evt-type').value = props.event_type || 'event';
    document.getElementById('evt-description').value = props.description || '';
    // Room / location
    if (props.room_id) {
        document.getElementById('loc-type-room').checked = true;
        document.getElementById('evt-room').value = String(props.room_id);
        document.getElementById('evt-location').value = '';
    } else {
        document.getElementById('loc-type-free').checked = true;
        document.getElementById('evt-location').value = props.location || '';
        document.getElementById('evt-room').value = '';
    }
    toggleLocationType();
    document.getElementById('evt-visibility').value = props.visibility || 'public';

    const isAllDay = fcEvent.allDay;
    document.getElementById('evt-allday').checked = isAllDay;
    toggleAllDay();

    const start = fcEvent.start;
    document.getElementById('evt-start-date').value = formatDateInput(start);
    if (!isAllDay) {
        document.getElementById('evt-start-time').value = formatTimeInput(start);
    }

    if (fcEvent.end) {
        const end = isAllDay ? new Date(fcEvent.end.getTime() - 86400000) : fcEvent.end;
        document.getElementById('evt-end-date').value = formatDateInput(end);
        if (!isAllDay) document.getElementById('evt-end-time').value = formatTimeInput(end);
    } else {
        document.getElementById('evt-end-date').value = formatDateInput(start);
    }

    document.getElementById('evt-recurrence').value = props.recurrence_rule || '';
    if (props.recurrence_rule) {
        document.getElementById('recurrence-end-group').classList.remove('d-none');
    }

    // Show delete button only for own events
    const deleteBtn = document.getElementById('evt-delete-btn');
    if (props.creator_id === currentUserId) {
        deleteBtn.classList.remove('d-none');
    } else {
        deleteBtn.classList.add('d-none');
    }

    // Color
    const evtColor = fcEvent.backgroundColor || userColors[currentUserId] || '#3788d8';
    document.getElementById('evt-color').value = evtColor;
    document.getElementById('evt-color-default').checked = !fcEvent.backgroundColor;
    document.getElementById('evt-color').disabled = !fcEvent.backgroundColor;

    new bootstrap.Modal(document.getElementById('eventModal')).show();

    // Load event details for reminder
    api.get(`/api/calendar/events/${fcEvent.id}`).then(detail => {
        const reminderSel = document.getElementById('evt-reminder');
        if (detail.my_reminder_minutes != null) {
            reminderSel.value = String(detail.my_reminder_minutes);
        } else {
            reminderSel.value = '';
        }
    }).catch(() => {});
}

async function saveEvent() {
    const title = document.getElementById('evt-title').value.trim();
    if (!title) {
        document.getElementById('evt-title').classList.add('is-invalid');
        return;
    }
    document.getElementById('evt-title').classList.remove('is-invalid');

    const isAllDay = document.getElementById('evt-allday').checked;
    const startDate = document.getElementById('evt-start-date').value;
    const startTime = document.getElementById('evt-start-time').value || '00:00';
    const endDate = document.getElementById('evt-end-date').value || startDate;
    const endTime = document.getElementById('evt-end-time').value || '23:59';

    let startAt, endAt;
    if (isAllDay) {
        startAt = startDate + 'T00:00:00';
        endAt = endDate + 'T23:59:59';
    } else {
        startAt = startDate + 'T' + startTime + ':00';
        endAt = endDate + 'T' + endTime + ':00';
    }

    const useDefaultColor = document.getElementById('evt-color-default').checked;
    const color = useDefaultColor ? null : document.getElementById('evt-color').value;

    const recurrence = document.getElementById('evt-recurrence').value || null;
    const recurrenceEnd = document.getElementById('evt-recurrence-end').value || null;

    const attendeeSelect = document.getElementById('evt-attendees');
    const attendeeIds = Array.from(attendeeSelect.selectedOptions).map(o => parseInt(o.value));

    const reminderVal = document.getElementById('evt-reminder').value;
    const reminderMinutes = reminderVal ? parseInt(reminderVal) : null;

    const isRoomMode = document.getElementById('loc-type-room').checked;
    const roomId = isRoomMode ? (document.getElementById('evt-room').value || null) : null;
    const locationText = !isRoomMode ? (document.getElementById('evt-location').value.trim() || null) : null;

    const data = {
        title: title,
        description: document.getElementById('evt-description').value.trim() || null,
        event_type: document.getElementById('evt-type').value,
        start_at: startAt,
        end_at: endAt,
        all_day: isAllDay,
        room_id: roomId ? parseInt(roomId) : null,
        location: locationText,
        color: color,
        visibility: document.getElementById('evt-visibility').value,
        recurrence_rule: recurrence,
        recurrence_end: recurrenceEnd,
    };

    const eventId = document.getElementById('evt-id').value;
    const saveBtn = document.getElementById('evt-save-btn');
    saveBtn.disabled = true;

    try {
        if (eventId) {
            await api.put(`/api/calendar/events/${eventId}`, data);
            // Update reminder
            if (reminderMinutes != null) {
                await api.put(`/api/calendar/events/${eventId}/reminder`, { minutes_before: reminderMinutes });
            } else {
                await api.del(`/api/calendar/events/${eventId}/reminder`).catch(() => {});
            }
        } else {
            data.attendee_ids = attendeeIds;
            data.reminder_minutes = reminderMinutes;
            await api.post('/api/calendar/events', data);
        }
        bootstrap.Modal.getInstance(document.getElementById('eventModal')).hide();
        reloadEvents();
        showToast(eventId ? 'Event updated' : 'Event created', 'success');
    } catch (e) {
        showToast(e.message, 'danger');
    } finally {
        saveBtn.disabled = false;
    }
}

async function deleteEvent() {
    const eventId = document.getElementById('evt-id').value;
    if (!eventId) return;
    if (!confirm('Delete this event?')) return;

    try {
        await api.del(`/api/calendar/events/${eventId}`);
        bootstrap.Modal.getInstance(document.getElementById('eventModal')).hide();
        reloadEvents();
        showToast('Event deleted', 'success');
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

async function handleEventMove(info) {
    const props = info.event.extendedProps;
    if (props.read_only || props.creator_id !== currentUserId) {
        info.revert();
        showToast('Cannot move this event', 'warning');
        return;
    }

    const moveData = {
        start_at: info.event.start.toISOString(),
        end_at: info.event.end ? info.event.end.toISOString() : null,
        all_day: info.event.allDay,
    };

    try {
        await api.put(`/api/calendar/events/${info.event.id}`, moveData);
    } catch (e) {
        info.revert();
        showToast(e.message, 'danger');
    }
}

// --- Settings ---

function openSettingsModal() {
    document.getElementById('set-view').value = settings.default_view || 'dayGridMonth';
    document.getElementById('set-color').value = settings.default_color || '#3788d8';
    document.getElementById('set-reminder').value = String(settings.default_reminder_minutes || 10);
    document.getElementById('set-wh-start').value = settings.working_hours_start || '09:00';
    document.getElementById('set-wh-end').value = settings.working_hours_end || '18:00';
    new bootstrap.Modal(document.getElementById('settingsModal')).show();
}

async function saveSettings() {
    const data = {
        default_view: document.getElementById('set-view').value,
        default_color: document.getElementById('set-color').value,
        default_reminder_minutes: parseInt(document.getElementById('set-reminder').value),
        working_hours_start: document.getElementById('set-wh-start').value,
        working_hours_end: document.getElementById('set-wh-end').value,
    };

    try {
        settings = await api.put('/api/calendar/settings', data);
        bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
        showToast('Settings saved', 'success');
        // Reload page to apply new settings
        location.reload();
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// --- Helpers ---

function toggleAllDay() {
    const allDay = document.getElementById('evt-allday').checked;
    document.getElementById('start-time-col').style.display = allDay ? 'none' : '';
    document.getElementById('end-time-col').style.display = allDay ? 'none' : '';
}

function toggleColorPicker() {
    const useDefault = document.getElementById('evt-color-default').checked;
    document.getElementById('evt-color').disabled = useDefault;
}

document.getElementById('evt-recurrence').addEventListener('change', function() {
    const show = this.value !== '';
    document.getElementById('recurrence-end-group').classList.toggle('d-none', !show);
});

function formatDateInput(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function formatTimeInput(d) {
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    return `${h}:${m}`;
}

// --- WebSocket + Notifications ---

function connectCalendarWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws/calendar`);
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'calendar_reminder' && data.user_id === currentUserId) {
            showDesktopNotification(data);
            showToast(`${data.title} — ${data.minutes_before} min`, 'info');
        }
        // Refresh on any calendar change
        reloadEvents();
    };
    ws.onclose = function() {
        setTimeout(connectCalendarWebSocket, 5000);
    };
    ws.onerror = function() { ws.close(); };
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showDesktopNotification(data) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(data.title, {
            body: `Starts in ${data.minutes_before} minutes` + (data.location ? ` | ${data.location}` : ''),
            tag: `event-${data.event_id}`,
        });
    }
}

init();
