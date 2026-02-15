"""OAuth provider abstraction and registry."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class OAuthUserInfo:
    """Normalized user info from an OAuth provider."""

    provider_user_id: str
    email: Optional[str]
    display_name: Optional[str]


class OAuthProviderConfig:
    """Base class for provider-specific configuration."""

    name: str = ""

    def parse_userinfo(self, data: dict) -> OAuthUserInfo:
        """Parse provider-specific userinfo response into OAuthUserInfo."""
        raise NotImplementedError


# Provider registry
_REGISTRY: Dict[str, OAuthProviderConfig] = {}


def register_provider(config: OAuthProviderConfig) -> None:
    _REGISTRY[config.name] = config


def get_provider_config(name: str) -> Optional[OAuthProviderConfig]:
    return _REGISTRY.get(name)


# Auto-register built-in providers
def _init_registry() -> None:
    from app.core.auth.oauth.github import GitHubProviderConfig
    from app.core.auth.oauth.google import GoogleProviderConfig

    register_provider(GoogleProviderConfig())
    register_provider(GitHubProviderConfig())


_init_registry()
