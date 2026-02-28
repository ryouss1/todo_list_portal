"""Fernet-based encryption for sensitive credentials (FTP/SMB passwords)."""

import logging

from portal_core.config import CREDENTIAL_ENCRYPTION_KEY

logger = logging.getLogger("app.core.encryption")

_fernet = None


def _get_fernet():
    """Lazy-initialize Fernet instance from CREDENTIAL_ENCRYPTION_KEY."""
    global _fernet
    if _fernet is None:
        if not CREDENTIAL_ENCRYPTION_KEY:
            raise ValueError(
                "CREDENTIAL_ENCRYPTION_KEY is not set. "
                "Generate a key with: python -c "
                '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        from cryptography.fernet import Fernet

        _fernet = Fernet(CREDENTIAL_ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext. Returns plaintext string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def mask_username(username: str) -> str:
    """Mask username for display: show first and last char only."""
    if not username or len(username) <= 2:
        return "****"
    return username[0] + "****" + username[-1]


def is_encryption_available() -> bool:
    """Check if encryption key is configured."""
    return bool(CREDENTIAL_ENCRYPTION_KEY)
