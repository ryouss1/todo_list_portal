"""Re-export from portal_core for backward compatibility."""

from portal_core.crud.oauth_provider import (  # noqa: F401
    create_provider,
    delete_provider,
    get_enabled_providers,
    get_provider,
    get_provider_by_name,
    get_providers,
    update_provider,
)
