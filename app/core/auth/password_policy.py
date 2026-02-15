"""Password strength validation."""

import re
import string

from app import config
from app.core.exceptions import ConflictError


def validate_password(password: str) -> None:
    """Validate password against configured policy. Raises ConflictError on violation."""
    errors = []

    if len(password) < config.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters")

    if len(password) > config.PASSWORD_MAX_LENGTH:
        errors.append(f"Password must be at most {config.PASSWORD_MAX_LENGTH} characters")

    if config.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if config.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if config.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if config.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[" + re.escape(string.punctuation) + r"]", password):
        errors.append("Password must contain at least one special character")

    if errors:
        raise ConflictError("; ".join(errors))
