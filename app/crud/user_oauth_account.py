"""Re-export from portal_core for backward compatibility."""

from portal_core.crud.user_oauth_account import (  # noqa: F401
    count_by_user,
    create_account,
    delete_account,
    get_by_provider_user,
    get_by_user,
    get_by_user_and_provider,
)
