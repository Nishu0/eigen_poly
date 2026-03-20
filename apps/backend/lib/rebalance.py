"""
Auto-rebalance engine — find best yield on Base, deploy idle USDC automatically.

Protocol support:
  ERC4626 (pool_id from DefiLlama = vault contract): Morpho, Fluid, Euler
  Aave v3:     Pool.supply() / Pool.withdraw()
  Compound v3: Comet.supply() / Comet.withdraw()

All thresholds configurable via environment variables:
  BASE_RPC_URL              Base RPC endpoint (default: https://mainnet.base.org)
  BASE_USDC_ADDRESS         USDC on Base (default: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
  AAVE_V3_POOL_BASE         Aave v3 Pool (default: 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5)
  AAVE_V3_AUSDC_BASE        Aave v3 aUSDC (default: 0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB)
  COMPOUND_V3_COMET_BASE    Compound v3 Comet (default: 0xb125E6687d4313864e53df431d5425969c15Eb2)
  REBALANCE_MIN_USDC        Min idle USDC to invest (default: 10.0)
  REBALANCE_APY_THRESHOLD   Min APY improvement to trigger rebalance (default: 0.5)
  REBALANCE_INTERVAL_HOURS  Cron interval (default: 3)
  REBALANCE_MIN_TVL         Min vault TVL via DefiLlama (default: 1000000)
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

import httpx
from web3 import Web3

from lib.agent_store import AgentStore, Agent
from lib.database import get_pool
from lib.tee_wallet import derive_wallet

log = logging.getLogger("rebalance")


def _env(key, default):
    return os.environ.get(key, default)


BASE_CHAIN_ID = 8453
MAX_UINT256 = 2**256 - 1

PROTOCOL_TYPES = {
    "morpho": "erc4626",
    "fluid": "erc4626",
    "euler": "erc4626",
    "aave-v3": "aave",
    "compound-v3": "compound",
}

TRACKED_PROTOCOLS = {
    "morpho": "Morpho",
    "fluid": "Fluid",
    "euler": "Euler",
    "aave-v3": "Aave v3",
    "compound-v3": "Compound v3",
}

# ── ABIs ──────────────────────────────────────────────────────────────────────

ERC20_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "allowance",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]

ERC4626_ABI = [
    {
        "name": "deposit",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "assets", "type": "uint256"},
            {"name": "receiver", "type": "address"},
        ],
        "outputs": [{"name": "shares", "type": "uint256"}],
    },
    {
        "name": "redeem",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "shares", "type": "uint256"},
            {"name": "receiver", "type": "address"},
            {"name": "owner", "type": "address"},
        ],
        "outputs": [{"name": "assets", "type": "uint256"}],
    },
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "previewRedeem",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "shares", "type": "uint256"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "previewDeposit",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "assets", "type": "uint256"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

AAVE_POOL_ABI = [
    {
        "name": "supply",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "onBehalfOf", "type": "address"},
            {"name": "referralCode", "type": "uint16"},
        ],
        "outputs": [],
    },
    {
        "name": "withdraw",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "to", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

COMPOUND_COMET_ABI = [
    {
        "name": "supply",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "name": "withdraw",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

# ── Web3 + tx helpers (sync, called via run_in_executor) ──────────────────────


def _get_w3() -> Web3:
    rpc = _env("BASE_RPC_URL", "https://mainnet.base.org")
    return Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))


def _cs(addr: str) -> str:
    return Web3.to_checksum_address(addr)


def _build_tx(w3: Web3, from_addr: str, contract_fn) -> dict:
    block = w3.eth.get_block("latest")
    base_fee = block.get("baseFeePerGas", 1_000_000)
    priority_fee = 100_000
    max_fee = base_fee * 2 + priority_fee
    tx = contract_fn.build_transaction(
        {
            "from": _cs(from_addr),
            "nonce": w3.eth.get_transaction_count(_cs(from_addr), "pending"),
            "chainId": BASE_CHAIN_ID,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        }
    )
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
    except Exception:
        tx["gas"] = 400_000
    return tx


def _sign_send_wait(w3: Web3, private_key: str, tx: dict) -> str:
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"tx reverted: {tx_hash.hex()}")
    return tx_hash.hex()


# ── USDC + approval helpers ───────────────────────────────────────────────────


def _usdc_balance_raw(w3: Web3, address: str) -> int:
    usdc = w3.eth.contract(
        address=_cs(_env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")),
        abi=ERC20_ABI,
    )
    return usdc.functions.balanceOf(_cs(address)).call()


def _ensure_approval(
    w3: Web3, private_key: str, owner: str, spender: str, amount_raw: int
) -> Optional[str]:
    usdc_addr = _cs(
        _env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    )
    usdc = w3.eth.contract(address=usdc_addr, abi=ERC20_ABI)
    current = usdc.functions.allowance(_cs(owner), _cs(spender)).call()
    if current >= amount_raw:
        return None
    tx = _build_tx(w3, owner, usdc.functions.approve(_cs(spender), MAX_UINT256))
    return _sign_send_wait(w3, private_key, tx)


# ── ERC4626 ───────────────────────────────────────────────────────────────────


def _deposit_erc4626(
    w3: Web3, private_key: str, agent_addr: str, vault_addr: str, amount_raw: int
) -> tuple[str, int]:
    """Approve (if needed) and deposit into ERC4626 vault. Returns (tx_hash, total_shares_after)."""
    vault = w3.eth.contract(address=_cs(vault_addr), abi=ERC4626_ABI + ERC20_ABI)
    _ensure_approval(w3, private_key, agent_addr, vault_addr, amount_raw)
    tx = _build_tx(w3, agent_addr, vault.functions.deposit(amount_raw, _cs(agent_addr)))
    tx_hash = _sign_send_wait(w3, private_key, tx)
    # Read total shares after deposit — covers both fresh deposit and topup
    shares = vault.functions.balanceOf(_cs(agent_addr)).call()
    return tx_hash, shares


def _withdraw_erc4626(
    w3: Web3, private_key: str, agent_addr: str, vault_addr: str, shares_raw: int
) -> tuple[str, int]:
    """Redeem all shares from ERC4626 vault. Returns (tx_hash, usdc_balance_raw_after)."""
    vault = w3.eth.contract(address=_cs(vault_addr), abi=ERC4626_ABI)
    tx = _build_tx(
        w3,
        agent_addr,
        vault.functions.redeem(shares_raw, _cs(agent_addr), _cs(agent_addr)),
    )
    tx_hash = _sign_send_wait(w3, private_key, tx)
    usdc_raw = _usdc_balance_raw(w3, agent_addr)
    return tx_hash, usdc_raw


def _current_value_erc4626(w3: Web3, vault_addr: str, shares_raw: int) -> float:
    vault = w3.eth.contract(address=_cs(vault_addr), abi=ERC4626_ABI)
    try:
        assets = vault.functions.previewRedeem(shares_raw).call()
        return assets / 1e6
    except Exception:
        return 0.0


# ── Aave v3 ───────────────────────────────────────────────────────────────────


def _deposit_aave(
    w3: Web3, private_key: str, agent_addr: str, amount_raw: int
) -> str:
    pool_addr = _env("AAVE_V3_POOL_BASE", "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
    usdc_addr = _env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    _ensure_approval(w3, private_key, agent_addr, pool_addr, amount_raw)
    pool = w3.eth.contract(address=_cs(pool_addr), abi=AAVE_POOL_ABI)
    tx = _build_tx(
        w3,
        agent_addr,
        pool.functions.supply(_cs(usdc_addr), amount_raw, _cs(agent_addr), 0),
    )
    return _sign_send_wait(w3, private_key, tx)


def _withdraw_aave(
    w3: Web3, private_key: str, agent_addr: str
) -> tuple[str, int]:
    pool_addr = _env("AAVE_V3_POOL_BASE", "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
    usdc_addr = _env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    pool = w3.eth.contract(address=_cs(pool_addr), abi=AAVE_POOL_ABI)
    tx = _build_tx(
        w3,
        agent_addr,
        pool.functions.withdraw(_cs(usdc_addr), MAX_UINT256, _cs(agent_addr)),
    )
    tx_hash = _sign_send_wait(w3, private_key, tx)
    return tx_hash, _usdc_balance_raw(w3, agent_addr)


def _aave_balance(w3: Web3, agent_addr: str) -> float:
    ausdc_addr = _env("AAVE_V3_AUSDC_BASE", "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB")
    token = w3.eth.contract(address=_cs(ausdc_addr), abi=ERC20_ABI)
    try:
        return token.functions.balanceOf(_cs(agent_addr)).call() / 1e6
    except Exception:
        return 0.0


# ── Compound v3 ───────────────────────────────────────────────────────────────


def _deposit_compound(
    w3: Web3, private_key: str, agent_addr: str, amount_raw: int
) -> str:
    comet_addr = _env("COMPOUND_V3_COMET_BASE", "0xb125E6687d4313864e53df431d5425969c15Eb2")
    usdc_addr = _env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    _ensure_approval(w3, private_key, agent_addr, comet_addr, amount_raw)
    comet = w3.eth.contract(address=_cs(comet_addr), abi=COMPOUND_COMET_ABI)
    tx = _build_tx(w3, agent_addr, comet.functions.supply(_cs(usdc_addr), amount_raw))
    return _sign_send_wait(w3, private_key, tx)


def _withdraw_compound(
    w3: Web3, private_key: str, agent_addr: str
) -> tuple[str, int]:
    comet_addr = _env("COMPOUND_V3_COMET_BASE", "0xb125E6687d4313864e53df431d5425969c15Eb2")
    usdc_addr = _env("BASE_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    comet = w3.eth.contract(address=_cs(comet_addr), abi=COMPOUND_COMET_ABI)
    balance_raw = comet.functions.balanceOf(_cs(agent_addr)).call()
    tx = _build_tx(w3, agent_addr, comet.functions.withdraw(_cs(usdc_addr), balance_raw))
    tx_hash = _sign_send_wait(w3, private_key, tx)
    return tx_hash, _usdc_balance_raw(w3, agent_addr)


def _compound_balance(w3: Web3, agent_addr: str) -> float:
    comet_addr = _env("COMPOUND_V3_COMET_BASE", "0xb125E6687d4313864e53df431d5425969c15Eb2")
    comet = w3.eth.contract(address=_cs(comet_addr), abi=COMPOUND_COMET_ABI)
    try:
        return comet.functions.balanceOf(_cs(agent_addr)).call() / 1e6
    except Exception:
        return 0.0


# ── DefiLlama fetch (async) ───────────────────────────────────────────────────


async def _fetch_best_vault() -> Optional[dict]:
    """Fetch best USDC vault on Base from DefiLlama. Returns vault dict or None."""
    min_tvl = float(_env("REBALANCE_MIN_TVL", "1000000"))
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get("https://yields.llama.fi/pools")
            if resp.status_code != 200:
                return None
            pools = resp.json().get("data", [])
    except Exception as e:
        log.warning(f"DefiLlama fetch failed: {e}")
        return None

    vaults = []
    for pool in pools:
        if (pool.get("chain") or "").lower() != "base":
            continue
        project = (pool.get("project") or "").lower()
        if project not in PROTOCOL_TYPES:
            continue
        if "USDC" not in (pool.get("symbol") or "").upper():
            continue
        tvl = pool.get("tvlUsd") or 0
        apy = pool.get("apy") or 0
        if tvl < min_tvl or apy <= 0:
            continue
        vaults.append(
            {
                "protocol": project,
                "protocol_name": TRACKED_PROTOCOLS[project],
                "pool_id": pool.get("pool", ""),
                "apy": round(apy, 4),
                "tvl_usd": round(tvl, 2),
                "type": PROTOCOL_TYPES[project],
            }
        )

    if not vaults:
        return None
    vaults.sort(key=lambda v: v["apy"], reverse=True)
    return vaults[0]


# ── DB helpers (async) ────────────────────────────────────────────────────────


async def _get_active_position(agent_id: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM vault_positions WHERE agent_id=$1 AND status='active' ORDER BY deposited_at DESC LIMIT 1",
        agent_id,
    )
    return dict(row) if row else None


async def _create_position(
    agent_id: str,
    protocol: str,
    protocol_name: str,
    pool_id: str,
    amount_usdc: float,
    shares: int,
    apy: float,
    deposit_tx: str,
) -> str:
    db = get_pool()
    pos_id = f"vp_{uuid.uuid4().hex[:12]}"
    await db.execute(
        """INSERT INTO vault_positions
           (position_id, agent_id, protocol, protocol_name, pool_id, amount_usdc, shares_held, apy_at_entry, deposit_tx)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
        pos_id,
        agent_id,
        protocol,
        protocol_name,
        pool_id,
        amount_usdc,
        str(shares),
        apy,
        deposit_tx,
    )
    return pos_id


async def _close_position(position_id: str, withdraw_tx: str) -> None:
    db = get_pool()
    await db.execute(
        "UPDATE vault_positions SET status='withdrawn', withdrawn_at=NOW(), withdraw_tx=$1 WHERE position_id=$2",
        withdraw_tx,
        position_id,
    )


async def _topup_position(position_id: str, additional_usdc: float, new_shares: int) -> None:
    db = get_pool()
    await db.execute(
        "UPDATE vault_positions SET amount_usdc=amount_usdc+$1, shares_held=$2 WHERE position_id=$3",
        additional_usdc,
        str(new_shares),
        position_id,
    )


async def _log_action(
    agent_id: str,
    action: str,
    from_protocol: Optional[str] = None,
    from_pool_id: Optional[str] = None,
    to_protocol: Optional[str] = None,
    to_pool_id: Optional[str] = None,
    amount_usdc: Optional[float] = None,
    apy: Optional[float] = None,
    shares: Optional[Any] = None,
    tx_hash: Optional[str] = None,
    reason: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    db = get_pool()
    await db.execute(
        """INSERT INTO vault_logs
           (log_id, agent_id, action, from_protocol, from_pool_id, to_protocol, to_pool_id,
            amount_usdc, apy, shares, tx_hash, reason, error)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
        f"vl_{uuid.uuid4().hex[:12]}",
        agent_id,
        action,
        from_protocol,
        from_pool_id,
        to_protocol,
        to_pool_id,
        amount_usdc,
        apy,
        str(shares) if shares is not None else None,
        tx_hash,
        reason,
        error,
    )


# ── Core rebalance logic ──────────────────────────────────────────────────────


async def run_rebalance_for_agent(agent: Agent) -> dict:
    """Run full rebalance cycle for one agent. Returns result dict."""
    loop = asyncio.get_event_loop()
    min_usdc = float(_env("REBALANCE_MIN_USDC", "10.0"))
    apy_threshold = float(_env("REBALANCE_APY_THRESHOLD", "0.5"))

    result: dict = {"agent_id": agent.agent_id, "action": "skip", "reason": "", "error": None}

    # 1. Fetch best vault
    best = await _fetch_best_vault()
    if not best:
        result["reason"] = "no vaults available from DefiLlama"
        await _log_action(agent.agent_id, "skip", reason=result["reason"])
        return result

    result["best_vault"] = best

    # 2. Get wallet
    try:
        wallet = derive_wallet(agent.wallet_index)
    except Exception as e:
        result["error"] = f"wallet derivation failed: {e}"
        await _log_action(agent.agent_id, "error", error=result["error"])
        return result

    agent_addr = wallet.address
    private_key = wallet.private_key

    # 3. Check idle USDC on Base EOA
    try:
        w3 = await loop.run_in_executor(None, _get_w3)
        idle_raw = await loop.run_in_executor(None, _usdc_balance_raw, w3, agent_addr)
        idle_usdc = idle_raw / 1e6
    except Exception as e:
        result["error"] = f"balance check failed: {e}"
        await _log_action(agent.agent_id, "error", error=result["error"])
        return result

    result["idle_usdc"] = idle_usdc

    # 4. Get current active position
    current = await _get_active_position(agent.agent_id)

    # 5. Decide action
    if current:
        current_protocol = current["protocol"]
        current_pool_id = current["pool_id"]
        current_apy = current["apy_at_entry"]
        best_apy = best["apy"]
        apy_improvement = best_apy - current_apy

        should_rebalance = (
            current_protocol != best["protocol"] and apy_improvement >= apy_threshold
        )

        if should_rebalance:
            # Withdraw from current, then deposit into best below
            log.info(
                f"[{agent.agent_id}] Rebalancing {current_protocol} → {best['protocol']}"
                f" (+{apy_improvement:.2f}% APY)"
            )
            try:
                protocol_type = PROTOCOL_TYPES.get(current_protocol, "erc4626")
                if protocol_type == "erc4626":
                    shares_raw = int(current["shares_held"])
                    withdraw_tx, new_idle_raw = await loop.run_in_executor(
                        None,
                        _withdraw_erc4626,
                        w3,
                        private_key,
                        agent_addr,
                        current_pool_id,
                        shares_raw,
                    )
                elif protocol_type == "aave":
                    withdraw_tx, new_idle_raw = await loop.run_in_executor(
                        None, _withdraw_aave, w3, private_key, agent_addr
                    )
                else:  # compound
                    withdraw_tx, new_idle_raw = await loop.run_in_executor(
                        None, _withdraw_compound, w3, private_key, agent_addr
                    )

                await _close_position(current["position_id"], withdraw_tx)
                await _log_action(
                    agent.agent_id,
                    "withdraw",
                    from_protocol=current_protocol,
                    from_pool_id=current_pool_id,
                    amount_usdc=current["amount_usdc"],
                    apy=current_apy,
                    tx_hash=withdraw_tx,
                    reason=f"rebalancing to {best['protocol']} (+{apy_improvement:.2f}% APY)",
                )

                # Re-read idle balance after withdraw
                new_idle_raw = await loop.run_in_executor(
                    None, _usdc_balance_raw, w3, agent_addr
                )
                idle_usdc = new_idle_raw / 1e6
                idle_raw = new_idle_raw
                current = None  # will deposit fresh below
                result["_was_rebalance"] = True

            except Exception as e:
                result["error"] = f"withdraw failed: {e}"
                await _log_action(
                    agent.agent_id,
                    "error",
                    from_protocol=current_protocol,
                    error=result["error"],
                )
                return result

        elif idle_usdc >= min_usdc:
            # Top up existing position with idle funds
            log.info(
                f"[{agent.agent_id}] Topping up {current_protocol} with {idle_usdc:.2f} USDC"
            )
            try:
                invest_raw = idle_raw
                protocol_type = PROTOCOL_TYPES.get(current_protocol, "erc4626")
                if protocol_type == "erc4626":
                    deposit_tx, new_shares = await loop.run_in_executor(
                        None,
                        _deposit_erc4626,
                        w3,
                        private_key,
                        agent_addr,
                        current_pool_id,
                        invest_raw,
                    )
                elif protocol_type == "aave":
                    deposit_tx = await loop.run_in_executor(
                        None, _deposit_aave, w3, private_key, agent_addr, invest_raw
                    )
                    new_shares = 0
                else:  # compound
                    deposit_tx = await loop.run_in_executor(
                        None, _deposit_compound, w3, private_key, agent_addr, invest_raw
                    )
                    new_shares = 0

                await _topup_position(current["position_id"], idle_usdc, new_shares)
                await _log_action(
                    agent.agent_id,
                    "topup",
                    to_protocol=current_protocol,
                    to_pool_id=current_pool_id,
                    amount_usdc=idle_usdc,
                    apy=current_apy,
                    shares=new_shares,
                    tx_hash=deposit_tx,
                    reason="idle funds detected, topping up existing position",
                )
                result["action"] = "topup"
                result["amount_usdc"] = idle_usdc
                result["tx_hash"] = deposit_tx
                return result

            except Exception as e:
                result["error"] = f"topup failed: {e}"
                await _log_action(agent.agent_id, "error", error=result["error"])
                return result

        else:
            # Current position exists, no idle funds above minimum, no better rate
            reason = (
                f"already in {current['protocol_name']} at {current_apy:.2f}% APY,"
                f" idle {idle_usdc:.2f} USDC below minimum {min_usdc}"
            )
            result["reason"] = reason
            result["action"] = "skip"
            await _log_action(agent.agent_id, "skip", reason=reason)
            return result

    # 6. Fresh deposit (no current position, or just withdrew for rebalance)
    if idle_usdc < min_usdc:
        reason = f"idle USDC {idle_usdc:.2f} below minimum {min_usdc}"
        result["reason"] = reason
        await _log_action(agent.agent_id, "skip", reason=reason)
        return result

    invest_raw = idle_raw
    invest_usdc = idle_usdc
    log.info(
        f"[{agent.agent_id}] Depositing {invest_usdc:.2f} USDC"
        f" into {best['protocol_name']} at {best['apy']:.2f}% APY"
    )

    try:
        protocol_type = best["type"]
        if protocol_type == "erc4626":
            deposit_tx, shares = await loop.run_in_executor(
                None,
                _deposit_erc4626,
                w3,
                private_key,
                agent_addr,
                best["pool_id"],
                invest_raw,
            )
        elif protocol_type == "aave":
            deposit_tx = await loop.run_in_executor(
                None, _deposit_aave, w3, private_key, agent_addr, invest_raw
            )
            shares = 0
        else:  # compound
            deposit_tx = await loop.run_in_executor(
                None, _deposit_compound, w3, private_key, agent_addr, invest_raw
            )
            shares = 0

        await _create_position(
            agent.agent_id,
            best["protocol"],
            best["protocol_name"],
            best["pool_id"],
            invest_usdc,
            shares,
            best["apy"],
            deposit_tx,
        )

        action = "rebalance" if result.get("_was_rebalance") else "deposit"
        await _log_action(
            agent.agent_id,
            action,
            to_protocol=best["protocol"],
            to_pool_id=best["pool_id"],
            amount_usdc=invest_usdc,
            apy=best["apy"],
            shares=shares,
            tx_hash=deposit_tx,
            reason=f"best available yield: {best['protocol_name']} at {best['apy']:.2f}% APY",
        )

        result["action"] = action
        result["protocol"] = best["protocol_name"]
        result["amount_usdc"] = invest_usdc
        result["apy"] = best["apy"]
        result["tx_hash"] = deposit_tx

    except Exception as e:
        result["error"] = f"deposit failed: {e}"
        await _log_action(
            agent.agent_id, "error", to_protocol=best["protocol"], error=result["error"]
        )

    return result


async def run_rebalance_cron() -> None:
    """Run rebalance for all agents with auto_rebalance=True."""
    store = AgentStore()
    try:
        agents = await store.list_agents()
    except Exception as e:
        log.error(f"[cron] failed to list agents: {e}")
        return

    eligible = [a for a in agents if a.auto_rebalance]
    log.info(
        f"[cron] rebalance check — {len(eligible)}/{len(agents)} agents eligible"
    )

    for agent in eligible:
        try:
            result = await run_rebalance_for_agent(agent)
            log.info(
                f"[cron] {agent.agent_id}: {result.get('action')}"
                f" — {result.get('reason') or result.get('protocol', '')}"
            )
        except Exception as e:
            log.error(f"[cron] {agent.agent_id} unhandled error: {e}")


async def start_rebalance_cron() -> None:
    """Background cron loop. Starts 60s after server boot, then every REBALANCE_INTERVAL_HOURS."""
    interval_secs = int(_env("REBALANCE_INTERVAL_HOURS", "3")) * 3600
    await asyncio.sleep(60)  # let server finish startup
    log.info(f"[cron] rebalance cron started — interval: {interval_secs // 3600}h")
    while True:
        try:
            await run_rebalance_cron()
        except Exception as e:
            log.error(f"[cron] top-level error: {e}")
        await asyncio.sleep(interval_secs)


# ── Live position value helper (used in routes) ───────────────────────────────


async def get_position_current_value(position: dict) -> float:
    """Get live on-chain value of a vault position."""
    loop = asyncio.get_event_loop()
    protocol_type = PROTOCOL_TYPES.get(position["protocol"], "erc4626")
    agent = await AgentStore().get_agent(position["agent_id"])
    if not agent:
        return position["amount_usdc"]
    try:
        wallet = derive_wallet(agent.wallet_index)
        agent_addr = wallet.address
        w3 = await loop.run_in_executor(None, _get_w3)
        if protocol_type == "erc4626":
            shares = int(position["shares_held"])
            return await loop.run_in_executor(
                None, _current_value_erc4626, w3, position["pool_id"], shares
            )
        elif protocol_type == "aave":
            return await loop.run_in_executor(None, _aave_balance, w3, agent_addr)
        else:  # compound
            return await loop.run_in_executor(None, _compound_balance, w3, agent_addr)
    except Exception:
        return position["amount_usdc"]
