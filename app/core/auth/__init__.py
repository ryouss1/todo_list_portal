"""Re-export from portal_core for backward compatibility."""

from portal_core.core.auth import log_auth_event, validate_password  # noqa: F401

__all__ = ["validate_password", "log_auth_event"]
