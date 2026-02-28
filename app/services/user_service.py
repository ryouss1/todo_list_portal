"""Re-export from portal_core for backward compatibility."""

from portal_core.services.user_service import (  # noqa: F401
    change_password,
    create_user,
    delete_user,
    get_user,
    get_user_response,
    list_users,
    reset_password,
    unlock_user,
    update_user,
)
