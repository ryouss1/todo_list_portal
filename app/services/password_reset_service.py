"""Re-export from portal_core for backward compatibility."""

from portal_core.services.password_reset_service import (  # noqa: F401
    complete_password_reset,
    request_password_reset,
    validate_reset_token,
)
