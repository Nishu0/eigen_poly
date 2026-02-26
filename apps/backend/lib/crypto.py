"""Encryption utilities for server-managed wallet keys.

Uses Fernet (AES-128-CBC + HMAC-SHA256) symmetric encryption.
The master key lives ONLY in the EIGENPOLY_MASTER_KEY env var — never in the DB.

Security model:
- DB leak alone → useless (encrypted blobs without master key)
- Env leak alone → useless (master key without encrypted data)
- Both needed to decrypt — follow least-privilege access for each
"""

import os
import base64
import hashlib

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    """Get Fernet cipher from the master key env var.

    EIGENPOLY_MASTER_KEY can be any string — we derive a proper
    32-byte key via SHA-256 and base64-encode it for Fernet.
    """
    master = os.environ.get("EIGENPOLY_MASTER_KEY", "")
    if not master:
        raise ValueError(
            "EIGENPOLY_MASTER_KEY env var is required for wallet encryption. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    # Derive a consistent 32-byte key from any string
    derived = hashlib.sha256(master.encode()).digest()
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_private_key(private_key: str) -> str:
    """Encrypt a private key. Returns a base64-encoded ciphertext string."""
    f = _get_fernet()
    return f.encrypt(private_key.encode()).decode()


def decrypt_private_key(encrypted: str) -> str:
    """Decrypt a private key from its encrypted form."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()
