"""Re-export from portal_core for backward compatibility."""

from portal_core.crud.login_attempt import (  # noqa: F401
    count_recent_failures,
    create_attempt,
    delete_old_attempts,
)
