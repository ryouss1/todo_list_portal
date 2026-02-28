"""Re-export from portal_core for backward compatibility."""

from portal_core.services.oauth_service import (  # noqa: F401
    get_enabled_providers,
    get_user_links,
    handle_callback,
    initiate_oauth,
    link_oauth_account,
    unlink_oauth_account,
)
