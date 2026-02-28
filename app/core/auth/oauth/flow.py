"""Re-export from portal_core for backward compatibility."""

from portal_core.core.auth.oauth.flow import (  # noqa: F401
    build_authorize_url,
    exchange_code_for_token,
    fetch_userinfo,
    generate_code_challenge,
    generate_code_verifier,
    generate_state,
)
