"""TEE Wallet — derive per-agent wallets from the TEE-provided MNEMONIC.

In EigenCompute production:
  - MNEMONIC is injected by the KMS into the TEE enclave
  - Only the verified Docker image inside the TEE can access it
  - Even the operator cannot extract it

In local development:
  - Set MNEMONIC in .env for testing (use a throwaway mnemonic)
  - Falls back to individual key generation if no MNEMONIC is set

HD derivation path: m/44'/60'/0'/0/{agent_index}
"""

import os
from dataclasses import dataclass
from typing import Optional

from eth_account import Account

# Enable HD wallet features
Account.enable_unaudited_hdwallet_features()


@dataclass
class DerivedWallet:
    """A wallet derived from the TEE mnemonic."""
    address: str
    private_key: str
    index: int
    derivation_path: str


def _get_mnemonic() -> Optional[str]:
    """Get the TEE mnemonic from environment.

    In EigenCompute TEE: auto-injected by KMS
    In local dev: set MNEMONIC in .env
    """
    return os.environ.get("MNEMONIC", "").strip() or None


def is_tee_mode() -> bool:
    """Check if we're running with a TEE mnemonic (production or dev)."""
    return _get_mnemonic() is not None


def derive_wallet(index: int) -> DerivedWallet:
    """Derive a wallet for the given agent index from the TEE mnemonic.

    Uses BIP-44 path: m/44'/60'/0'/0/{index}
    """
    mnemonic = _get_mnemonic()
    if not mnemonic:
        raise RuntimeError(
            "No MNEMONIC available. In production this is provided by the TEE KMS. "
            "For local dev, set MNEMONIC in your .env file."
        )

    path = f"m/44'/60'/0'/0/{index}"
    account = Account.from_mnemonic(mnemonic, account_path=path)

    return DerivedWallet(
        address=account.address,
        private_key=account.key.hex(),
        index=index,
        derivation_path=path,
    )


def derive_address(index: int) -> str:
    """Derive just the address for an agent index (no private key returned)."""
    return derive_wallet(index).address


def sign_transaction(index: int, transaction: dict) -> bytes:
    """Sign a transaction using the wallet at the given index.

    The private key is derived in-memory, used for signing, then discarded.
    It is never written to disk or stored in any variable beyond this function.
    """
    wallet = derive_wallet(index)
    from web3 import Web3
    w3 = Web3()
    signed = w3.eth.account.sign_transaction(transaction, wallet.private_key)
    return signed.raw_transaction


def get_next_index_hint() -> int:
    """Get the next available index. Called during registration.

    The actual source of truth is the DB — this is just a hint.
    The register route queries max(wallet_index) + 1 from the agents table.
    """
    return 0  # DB will provide the real value
