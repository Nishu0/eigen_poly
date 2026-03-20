"""Wallet management - env var based."""

import os
from dataclasses import dataclass
from typing import Optional

from eth_abi import encode as abi_encode
from eth_account import Account
from web3 import Web3

from lib.contracts import CONTRACTS, ERC20_ABI, CTF_ABI, POLYGON_CHAIN_ID


@dataclass
class WalletBalances:
    """Wallet balances."""
    pol: float
    usdc_e: float


# Minimal Gnosis Safe ABI for execTransaction + nonce
GNOSIS_SAFE_ABI = [
    {
        "inputs": [],
        "name": "nonce",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "execTransaction",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "operation", "type": "uint8"},
            {"name": "safeTxGas", "type": "uint256"},
            {"name": "baseGas", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasToken", "type": "address"},
            {"name": "refundReceiver", "type": "address"},
            {"name": "signatures", "type": "bytes"},
        ],
        "outputs": [{"name": "success", "type": "bool"}],
    },
]

_DOMAIN_TYPEHASH = Web3.keccak(text="EIP712Domain(uint256 chainId,address verifyingContract)")
_SAFE_TX_TYPEHASH = Web3.keccak(
    text="SafeTx(address to,uint256 value,bytes data,uint8 operation,"
         "uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,"
         "address payable refundReceiver,uint256 nonce)"
)
_ZERO_ADDR = "0x" + "00" * 20


class WalletManager:
    """Manages wallet from POLYCLAW_PRIVATE_KEY env var or TEE mnemonic."""

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or os.environ.get("CHAINSTACK_NODE", "")
        self._private_key: Optional[str] = None
        self._address: Optional[str] = None
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load private key from POLYCLAW_PRIVATE_KEY env var."""
        private_key = os.environ.get("POLYCLAW_PRIVATE_KEY")
        if private_key:
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            account = Account.from_key(private_key)
            self._private_key = private_key
            self._address = account.address

    @classmethod
    def from_tee(cls, wallet_index: int, rpc_url: Optional[str] = None) -> "WalletManager":
        """Create a WalletManager from the TEE mnemonic for a specific agent.

        Derives the agent's private key from MNEMONIC + HD path m/44'/60'/0'/0/{index}.
        Falls back to POLYCLAW_PRIVATE_KEY if no MNEMONIC is available.
        """
        from lib.tee_wallet import derive_wallet, is_tee_mode

        mgr = cls.__new__(cls)
        mgr.rpc_url = rpc_url or os.environ.get("CHAINSTACK_NODE", "")
        mgr._private_key = None
        mgr._address = None

        if is_tee_mode():
            wallet = derive_wallet(wallet_index)
            key = wallet.private_key
            if not key.startswith("0x"):
                key = "0x" + key
            mgr._private_key = key
            mgr._address = wallet.address
        else:
            # Fallback to shared server key for local dev
            mgr._load_from_env()

        return mgr

    @property
    def is_unlocked(self) -> bool:
        """Check if wallet is available."""
        return self._private_key is not None

    @property
    def address(self) -> Optional[str]:
        """Get wallet address."""
        return self._address

    def _get_web3(self) -> Web3:
        """Get Web3 instance."""
        if not self.rpc_url:
            raise ValueError("CHAINSTACK_NODE environment variable not set")
        from web3.middleware import ExtraDataToPOAMiddleware
        w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 60}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return w3

    def get_unlocked_key(self) -> str:
        """Get the private key for signing."""
        if not self._private_key:
            raise ValueError("No wallet configured. Set POLYCLAW_PRIVATE_KEY env var.")
        return self._private_key

    def lock(self) -> None:
        """Clear private key from memory."""
        self._private_key = None

    def get_balances(self) -> WalletBalances:
        """Get POL and USDC.e balances for the EOA."""
        if not self._address:
            raise ValueError("No wallet configured")

        w3 = self._get_web3()
        checksum = Web3.to_checksum_address(self._address)

        pol = float(w3.from_wei(w3.eth.get_balance(checksum), "ether"))

        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["USDC_E"]),
            abi=ERC20_ABI,
        )
        usdc_balance = usdc.functions.balanceOf(checksum).call() / 1e6

        return WalletBalances(pol=pol, usdc_e=usdc_balance)

    def get_safe_usdc_balance(self, safe_address: str) -> float:
        """Get USDC.e balance of the Polymarket Safe."""
        w3 = self._get_web3()
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["USDC_E"]),
            abi=ERC20_ABI,
        )
        return usdc.functions.balanceOf(Web3.to_checksum_address(safe_address)).call() / 1e6

    def safe_exec(self, safe_address: str, to: str, data: bytes, gas: int = 350000) -> str:
        """Execute a transaction through the Gnosis Safe. EOA signs + pays gas.

        The Safe becomes msg.sender for the inner call — so USDC.e and tokens
        are pulled from / minted to the Safe, not the EOA.
        """
        if not self._private_key:
            raise ValueError("No wallet configured")

        w3 = self._get_web3()
        eoa = Web3.to_checksum_address(self._address)
        safe = Web3.to_checksum_address(safe_address)
        to_addr = Web3.to_checksum_address(to)

        safe_contract = w3.eth.contract(address=safe, abi=GNOSIS_SAFE_ABI)
        nonce = safe_contract.functions.nonce().call()

        # EIP-712 domain separator
        domain_sep = Web3.keccak(
            abi_encode(["bytes32", "uint256", "address"], [_DOMAIN_TYPEHASH, POLYGON_CHAIN_ID, safe])
        )

        # Safe transaction hash
        safe_tx_hash = Web3.keccak(
            abi_encode(
                ["bytes32", "address", "uint256", "bytes32", "uint8",
                 "uint256", "uint256", "uint256", "address", "address", "uint256"],
                [_SAFE_TX_TYPEHASH, to_addr, 0, Web3.keccak(data), 0,
                 0, 0, 0, _ZERO_ADDR, _ZERO_ADDR, nonce],
            )
        )

        # Final EIP-712 hash — sign this raw (no eth_sign prefix) → v = 27/28
        final_hash = Web3.keccak(b"\x19\x01" + domain_sep + safe_tx_hash)

        account = Account.from_key(self._private_key)
        sig = account._key_obj.sign_msg_hash(final_hash)
        signature = sig.r.to_bytes(32, "big") + sig.s.to_bytes(32, "big") + bytes([sig.v + 27])

        tx = safe_contract.functions.execTransaction(
            to_addr, 0, data, 0, 0, 0, 0, _ZERO_ADDR, _ZERO_ADDR, signature
        ).build_transaction({
            "from": eoa,
            "nonce": w3.eth.get_transaction_count(eoa),
            "gas": gas,
            "gasPrice": w3.eth.gas_price,
            "chainId": POLYGON_CHAIN_ID,
        })

        acct = w3.eth.account.from_key(self._private_key)
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt["status"] != 1:
            raise ValueError(f"Safe execTransaction failed: {tx_hash.hex()}")

        return tx_hash.hex()

    def check_approvals(self) -> bool:
        """Check if all Polymarket approvals are set."""
        if not self._address:
            return False

        w3 = self._get_web3()
        checksum = Web3.to_checksum_address(self._address)

        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["USDC_E"]),
            abi=ERC20_ABI,
        )
        ctf = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["CTF"]),
            abi=CTF_ABI,
        )

        # Check USDC approvals
        for contract in ["CTF", "CTF_EXCHANGE", "NEG_RISK_CTF_EXCHANGE"]:
            allowance = usdc.functions.allowance(checksum, CONTRACTS[contract]).call()
            if allowance == 0:
                return False

        # Check CTF approvals
        for contract in ["CTF_EXCHANGE", "NEG_RISK_CTF_EXCHANGE", "NEG_RISK_ADAPTER"]:
            approved = ctf.functions.isApprovedForAll(
                checksum, CONTRACTS[contract]
            ).call()
            if not approved:
                return False

        return True

    def set_approvals(self) -> list[str]:
        """Set all Polymarket contract approvals. Returns tx hashes."""
        if not self._private_key:
            raise ValueError("No wallet configured")

        w3 = self._get_web3()
        address = Web3.to_checksum_address(self._address)
        account = w3.eth.account.from_key(self._private_key)

        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["USDC_E"]),
            abi=ERC20_ABI,
        )
        ctf = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["CTF"]),
            abi=CTF_ABI,
        )

        MAX_UINT256 = 2**256 - 1
        tx_hashes = []

        approvals = [
            (usdc, "approve", CONTRACTS["CTF"], MAX_UINT256),
            (usdc, "approve", CONTRACTS["CTF_EXCHANGE"], MAX_UINT256),
            (usdc, "approve", CONTRACTS["NEG_RISK_CTF_EXCHANGE"], MAX_UINT256),
            (ctf, "setApprovalForAll", CONTRACTS["CTF_EXCHANGE"], True),
            (ctf, "setApprovalForAll", CONTRACTS["NEG_RISK_CTF_EXCHANGE"], True),
            (ctf, "setApprovalForAll", CONTRACTS["NEG_RISK_ADAPTER"], True),
        ]

        for contract, method, spender, value in approvals:
            fn = getattr(contract.functions, method)
            tx = fn(Web3.to_checksum_address(spender), value).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 100000,
                    "gasPrice": w3.eth.gas_price,
                    "chainId": POLYGON_CHAIN_ID,
                }
            )

            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] != 1:
                raise ValueError(f"Approval failed: {tx_hash.hex()}")

            tx_hashes.append(tx_hash.hex())

        return tx_hashes
