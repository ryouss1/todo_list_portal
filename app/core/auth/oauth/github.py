"""GitHub OAuth provider configuration."""

from app.core.auth.oauth.provider import OAuthProviderConfig, OAuthUserInfo


class GitHubProviderConfig(OAuthProviderConfig):
    name = "github"

    def parse_userinfo(self, data: dict) -> OAuthUserInfo:
        return OAuthUserInfo(
            provider_user_id=str(data.get("id", "")),
            email=data.get("email"),
            display_name=data.get("name") or data.get("login"),
        )
