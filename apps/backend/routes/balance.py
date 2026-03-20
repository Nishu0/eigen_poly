"""Balance route — multi-chain balances: Polygon EOA+Safe, Solana vault, Base EOA."""

import os
import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from web3 import Web3

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.contracts import CONTRACTS, ERC20_ABI, derive_polymarket_safe
from lib.database import get_pool
from routes.oauth import get_current_user


router = APIRouter()
store = AgentStore()

CHAIN_LOGOS = {
    "polygon": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/polygon/info/logo.png",
    "solana":  "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/solana/info/logo.png",
    "base":    "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/info/logo.png",
}
USDC_LOGO = "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/binance/assets/USDC-CD2/logo.png"

BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class ChainBalance(BaseModel):
    chain: str
    chain_logo: str
    address: str
    native: float
    native_symbol: str
    usdc: float
    usdc_logo: str = USDC_LOGO


class BalanceResponse(BaseModel):
    agentId: str
    polygon_eoa: ChainBalance
    polygon_safe: ChainBalance
    solana_wallet: ChainBalance
    base_eoa: ChainBalance
    total_usdc: float
    flags: dict


# ── chain helpers ─────────────────────────────────────────────────────────────

def _evm_balance(rpc_url: str, address: str, usdc_contract_addr: str) -> tuple[float, float]:
    """Return (native, usdc) for any EVM chain."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15, "proxies": {}}))
        cs = Web3.to_checksum_address(address)
        native = float(w3.from_wei(w3.eth.get_balance(cs), "ether"))
        usdc_c = w3.eth.contract(address=Web3.to_checksum_address(usdc_contract_addr), abi=ERC20_ABI)
        usdc = usdc_c.functions.balanceOf(cs).call() / 1e6
        return native, usdc
    except Exception as e:
        print(f"evm balance error [{address}]: {e}")
        return 0.0, 0.0


async def _solana_balance(address: str) -> tuple[float, float]:
    """Return (SOL, USDC) for a Solana address."""
    if not address or address == "not derived":
        return 0.0, 0.0
    rpc = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            sol_resp = await client.post(rpc, json={
                "jsonrpc": "2.0", "id": 1, "method": "getBalance",
                "params": [address],
            })
            lamports = sol_resp.json().get("result", {}).get("value", 0)

            tok_resp = await client.post(rpc, json={
                "jsonrpc": "2.0", "id": 2,
                "method": "getTokenAccountsByOwner",
                "params": [address, {"mint": SOLANA_USDC_MINT}, {"encoding": "jsonParsed"}],
            })
            accounts = tok_resp.json().get("result", {}).get("value", [])
            usdc = 0.0
            if accounts:
                usdc = float(
                    accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
                )
            return lamports / 1e9, usdc
    except Exception as e:
        print(f"solana balance error [{address}]: {e}")
        return 0.0, 0.0


# ── route ─────────────────────────────────────────────────────────────────────

@router.get("/balance/{agent_id}", response_model=BalanceResponse)
async def get_balance(
    agent_id: str,
    request: Request,
    api_key: Optional[str] = Header(default=None, alias="x-api-key"),
):
    """
    multi-chain balances for an agent.
    accepts either x-api-key header or session cookie (dashboard).
    - polygon eoa  (POL + USDC.e) — trading signer
    - polygon safe (POL + USDC.e) — polymarket proxy wallet
    - solana vault (SOL + USDC)   — metengine x402 payments
    - base eoa     (ETH + USDC)   — same address, base chain
    """
    if api_key and api_key.startswith("epk_"):
        key_hash = hash_api_key(api_key)
        agent = await store.get_agent_by_key_hash(key_hash)
        if not agent or agent.agent_id != agent_id:
            raise HTTPException(status_code=403, detail="API key does not match agent")
    else:
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="missing api key or session")
        agent = await store.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="agent not found")
        pool = get_pool()
        owner = await pool.fetchval("SELECT owner_id FROM agents WHERE agent_id = $1", agent_id)
        if owner != user["sub"]:
            raise HTTPException(status_code=403, detail="you do not own this agent")

    polygon_rpc = os.environ.get("CHAINSTACK_NODE", "")
    base_rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
    if not polygon_rpc:
        raise HTTPException(status_code=503, detail="polygon RPC not configured (CHAINSTACK_NODE)")

    safe_addr = agent.polygon_safe or derive_polymarket_safe(agent.wallet_address)
    solana_addr = agent.solana_wallet or ""

    loop = asyncio.get_event_loop()

    # kick off EVM queries in thread pool (blocking Web3 calls)
    pol_eoa_fut  = loop.run_in_executor(None, _evm_balance, polygon_rpc, agent.wallet_address, CONTRACTS["USDC_E"])
    pol_safe_fut = loop.run_in_executor(None, _evm_balance, polygon_rpc, safe_addr, CONTRACTS["USDC_E"])
    base_fut     = loop.run_in_executor(None, _evm_balance, base_rpc, agent.wallet_address, BASE_USDC)
    sol_coro     = _solana_balance(solana_addr)

    pol_eoa_native,  pol_eoa_usdc  = await pol_eoa_fut
    pol_safe_native, pol_safe_usdc = await pol_safe_fut
    base_native,     base_usdc     = await base_fut
    sol_native,      sol_usdc      = await sol_coro

    total_usdc = pol_eoa_usdc + pol_safe_usdc + base_usdc + sol_usdc

    return BalanceResponse(
        agentId=agent_id,
        polygon_eoa=ChainBalance(
            chain="polygon", chain_logo=CHAIN_LOGOS["polygon"],
            address=agent.wallet_address,
            native=round(pol_eoa_native, 6), native_symbol="POL",
            usdc=round(pol_eoa_usdc, 6),
        ),
        polygon_safe=ChainBalance(
            chain="polygon", chain_logo=CHAIN_LOGOS["polygon"],
            address=safe_addr,
            native=round(pol_safe_native, 6), native_symbol="POL",
            usdc=round(pol_safe_usdc, 6),
        ),
        solana_wallet=ChainBalance(
            chain="solana", chain_logo=CHAIN_LOGOS["solana"],
            address=solana_addr or "not derived",
            native=round(sol_native, 6), native_symbol="SOL",
            usdc=round(sol_usdc, 6),
        ),
        base_eoa=ChainBalance(
            chain="base", chain_logo=CHAIN_LOGOS["base"],
            address=agent.wallet_address,
            native=round(base_native, 6), native_symbol="ETH",
            usdc=round(base_usdc, 6),
        ),
        total_usdc=round(total_usdc, 6),
        flags={
            "auto_rebalance": agent.auto_rebalance,
            "auto_freemonies": agent.auto_freemonies,
        },
    )
