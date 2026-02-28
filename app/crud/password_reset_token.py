"""Re-export from portal_core for backward compatibility."""

from portal_core.crud.password_reset_token import (  # noqa: F401
    cleanup_expired,
    count_recent_tokens,
    create_token,
    get_by_token_hash,
    invalidate_user_tokens,
    mark_used,
)
