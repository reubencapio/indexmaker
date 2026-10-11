"""
Encryption for third-party credentials the application has to store and reuse.

A user's own password is hashed, because it only ever needs to be checked. An
SFTP password is different: it has to be presented to someone else's server, so
it must be recoverable -- which means encrypted, not hashed. Stored in the clear,
a single leaked database backup would hand over every customer's file server.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# Marks a value as ciphertext, so rows written before encryption was introduced
# are still readable and are never encrypted twice.
_PREFIX = "enc:v1:"


class SecretDecryptionError(Exception):
    """A stored secret could not be decrypted with the current key."""


def _fernet() -> Fernet:
    # A dedicated key if one is configured; otherwise one derived from
    # SECRET_KEY, so encryption works without extra deployment steps.
    material = settings.CREDENTIAL_ENCRYPTION_KEY or settings.SECRET_KEY
    digest = hashlib.sha256(f"indexmaker-credentials:{material}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a secret for storage. Empty values and ciphertext pass through."""
    if not value or value.startswith(_PREFIX):
        return value
    return _PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    """
    Recover a stored secret.

    Values without the prefix were stored before encryption existed and are
    returned as they are.

    Raises:
        SecretDecryptionError: if the key has changed since the value was stored.
    """
    if not value or not value.startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX) :].encode()).decode()
    except InvalidToken as exc:
        raise SecretDecryptionError(
            "Stored credential cannot be decrypted. Re-enter it to continue."
        ) from exc
