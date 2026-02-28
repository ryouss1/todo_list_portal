"""Re-export from portal_core for backward compatibility."""

from portal_core.core.auth.oauth.provider import (  # noqa: F401
    OAuthProviderConfig,
    OAuthUserInfo,
    get_provider_config,
    register_provider,
)
