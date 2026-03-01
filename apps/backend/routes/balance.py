"""Balance route — fetch EOA + Safe wallet balances for an agent."""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from web3 import Web3

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.contracts import CONTRACTS, ERC20_ABI, derive_polymarket_safe


router = APIRouter()
store = AgentStore()


class WalletBalance(BaseModel):
    address: str
    pol: float
    usdc_e: float


class BalanceResponse(BaseModel):
    agentId: str
    eoa: WalletBalance
    safe: WalletBalance
    total_usdc_e: float
    total_usd: float


def _get_balances(rpc_url: str, address: str) -> WalletBalance:
    """Get POL and USDC.e balances for an address on Polygon."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15, "proxies": {}}))
        checksum = Web3.to_checksum_address(address)

        pol = float(w3.from_wei(w3.eth.get_balance(checksum), "ether"))

        usdc_e = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["USDC_E"]),
            abi=ERC20_ABI,
        )
        usdc_balance = usdc_e.functions.balanceOf(checksum).call() / 1e6

        return WalletBalance(address=address, pol=pol, usdc_e=usdc_balance)
    except Exception as e:
        print(f"Warning: balance check failed for {address}: {e}")
        return WalletBalance(address=address, pol=0.0, usdc_e=0.0)


def _get_safe_address(eoa_address: str) -> str:
    """Derive Polymarket Safe address using CREATE2 (no RPC needed)."""
    try:
        return derive_polymarket_safe(eoa_address)
    except Exception:
        return ""


@router.get("/balance/{agent_id}", response_model=BalanceResponse)
async def get_balance(agent_id: str, api_key: str = Depends(require_api_key)):
    """Fetch EOA + Safe wallet balances for a registered agent.

    Returns USDC.e and POL balances for both:
    - **EOA wallet** — signing key, receives bridge deposits
    - **Safe wallet** — Polymarket proxy, holds trading positions
    """

    # Verify API key ownership
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    rpc_url = os.environ.get("CHAINSTACK_NODE", "")
    if not rpc_url:
        raise HTTPException(status_code=503, detail="RPC not configured")

    # Get EOA balances
    eoa = _get_balances(rpc_url, agent.wallet_address)

    # Get Safe address and balances
    safe_addr = _get_safe_address(agent.wallet_address)
    safe = _get_balances(rpc_url, safe_addr) if safe_addr else WalletBalance(address="", pol=0.0, usdc_e=0.0)

    total_usdc = eoa.usdc_e + safe.usdc_e

    return BalanceResponse(
        agentId=agent_id,
        eoa=eoa,
        safe=safe,
        total_usdc_e=total_usdc,
        total_usd=total_usdc,  # USDC.e ≈ $1
    )
