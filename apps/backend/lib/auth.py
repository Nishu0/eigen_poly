"""Authentication utilities — wallet signature verification and API key management."""

import hashlib
import hmac
import os
import secrets
from typing import Optional

from eth_account.messages import encode_defunct
from web3 import Web3
from fastapi import Header, HTTPException, Depends


API_KEY_PREFIX = "epk_"


def generate_api_key() -> str:
    """Generate a secure, scoped API key with prefix."""
    raw = secrets.token_hex(32)
    return f"{API_KEY_PREFIX}{raw}"


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify EIP-191 wallet signature.

    Returns True if the recovered address matches the claimed wallet address.
    """
    try:
        w3 = Web3()
        msg = encode_defunct(text=message)
        recovered = w3.eth.account.recover_message(msg, signature=signature)
        return recovered.lower() == wallet_address.lower()
    except Exception:
        return False


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage (never store raw keys)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def require_api_key(x_api_key: str = Header(..., alias="x-api-key")) -> str:
    """FastAPI dependency — validates x-api-key header.

    Returns the raw API key if present. Route handlers should verify
    the key against the agent store.
    """
    if not x_api_key or not x_api_key.startswith(API_KEY_PREFIX):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
