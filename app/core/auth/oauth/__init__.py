"""Re-export from portal_core for backward compatibility."""

from portal_core.core.auth.oauth import (  # noqa: F401
    OAuthProviderConfig,
    OAuthUserInfo,
    get_provider_config,
)

__all__ = ["OAuthProviderConfig", "OAuthUserInfo", "get_provider_config"]
