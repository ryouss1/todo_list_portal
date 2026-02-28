"""Re-export from portal_core for backward compatibility."""

from portal_core.core.encryption import (  # noqa: F401
    decrypt_value,
    encrypt_value,
    is_encryption_available,
    mask_username,
)
