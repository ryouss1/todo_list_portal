### Authorization Rules

- **Todos**: Owner-only CRUD; public todos visible to all via `/api/todos/public`
- **Reports**: All authenticated users can read all reports; only owner can edit/delete
- **Presence**: All users can view all statuses; only own status can be updated
- **Summary**: Read-only aggregation, accessible to all authenticated users
- **TaskList**: Unassigned items visible to all; assigned items visible to assignee + creator; edit by assignee/creator only
- **Attendance/Tasks**: Owner-only access
- **LogSources/AlertRules**: Admin-only create/update/delete; all authenticated users can read
- **Alerts**: All authenticated users can view/acknowledge; admin-only delete
- **Users**: Admin-only create/delete; all authenticated users can list/get; admin can edit any user (but not own role/is_active); non-admin can edit own display_name only