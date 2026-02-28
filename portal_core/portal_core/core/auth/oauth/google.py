"""Google OAuth provider configuration."""

from portal_core.core.auth.oauth.provider import OAuthProviderConfig, OAuthUserInfo


class GoogleProviderConfig(OAuthProviderConfig):
    name = "google"

    def parse_userinfo(self, data: dict) -> OAuthUserInfo:
        return OAuthUserInfo(
            provider_user_id=str(data.get("sub", "")),
            email=data.get("email"),
            display_name=data.get("name"),
        )
