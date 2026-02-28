"""Re-export from portal_core for backward compatibility."""

from portal_core.core.auth.rate_limiter import (  # noqa: F401
    check_account_locked,
    check_rate_limit,
    cleanup_old_attempts,
    maybe_lock_account,
    record_attempt,
    unlock_account,
)
