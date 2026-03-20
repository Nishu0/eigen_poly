"""Deposit routes — Polymarket Bridge API proxy.

Provides cross-chain deposit addresses, supported assets list,
and bridge quotes for funding agent wallets.

Bridge API base: https://bridge.polymarket.com
"""

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from web3 import Web3
from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.contracts import CONTRACTS, PROXY_WALLET_ABI

router = APIRouter(prefix="/deposit", tags=["deposit"])
store = AgentStore()

BRIDGE_BASE = "https://bridge.polymarket.com"

# USDC.e on Polygon — this is what Polymarket Safe uses, NOT native USDC
USDC_E_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_NATIVE_POLYGON = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"


# --- Helpers ---


def _get_safe_address(eoa_address: str) -> str:
    """Compute Polymarket Safe address from EOA on-chain."""
    rpc_url = os.environ.get("CHAINSTACK_NODE", "")
    if not rpc_url:
        return eoa_address
    try:
        from web3.middleware import ExtraDataToPOAMiddleware
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        exchange = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["CTF_EXCHANGE"]),
            abi=PROXY_WALLET_ABI,
        )
        return exchange.functions.getPolyProxyWalletAddress(
            Web3.to_checksum_address(eoa_address)
        ).call()
    except Exception:
        return eoa_address


# --- Models ---


ADDRESS_TYPE_CHAINS = {
    "evm": ["Ethereum", "Base", "Arbitrum", "Optimism", "and other EVM chains"],
    "svm": ["Solana"],
    "btc": ["Bitcoin"],
    "tvm": ["Tron"],
}


class DepositAddressRequest(BaseModel):
    agentId: Optional[str] = None
    safeAddress: Optional[str] = None  # Pass Safe wallet directly


class QuoteRequest(BaseModel):
    fromAmountBaseUnit: str  # e.g. "10000000" for 10 USDC
    fromChainId: str  # e.g. "1" for Ethereum
    fromTokenAddress: str  # source token contract
    toChainId: str = "137"  # default: Polygon
    toTokenAddress: str = USDC_E_POLYGON  # default: USDC.e on Polygon


# --- Routes ---


@router.get("/supported-assets")
async def get_supported_assets():
    """List all supported chains and tokens for depositing into Polymarket.

    Returns tokens from Ethereum, Polygon, Arbitrum, Base, Solana, Bitcoin, etc.
    Each entry includes chainId, chainName, token details, and minimum deposit in USD.

    **Important**: On Polygon, Polymarket uses USDC.e (0x2791...4174), NOT native USDC.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BRIDGE_BASE}/supported-assets")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()

    # Add a helpful note about USDC.e
    return {
        **data,
        "_note": (
            "On Polygon, Polymarket uses USDC.e (0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174), "
            "NOT native USDC (0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359). "
            "If sending USDC on Polygon directly to the Safe wallet, use USDC.e."
        ),
        "_usdc_e_polygon": USDC_E_POLYGON,
        "_usdc_native_polygon": USDC_NATIVE_POLYGON,
    }


@router.post("/address")
async def create_deposit_address(
    req: DepositAddressRequest,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
):
    """Get cross-chain deposit addresses for a Polymarket Safe wallet.

    Pass either:
    - `safeAddress` directly (no auth required — api_key ignored)
    - `agentId` + `x-api-key` header to auto-resolve the Safe from your registered agent

    Returns unique deposit addresses per chain type:
    - **evm** — Ethereum, Base, Arbitrum, Optimism, other EVM chains
    - **svm** — Solana
    - **btc** — Bitcoin
    - **tvm** — Tron

    Funds bridge automatically to USDC.e on your Polygon Safe wallet.
    """
    if req.safeAddress:
        safe_address = req.safeAddress
        eoa_address = None
        agent_id = None
    elif req.agentId:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required when using agentId")
        key_hash = hash_api_key(x_api_key)
        agent = await store.get_agent_by_key_hash(key_hash)
        if not agent or agent.agent_id != req.agentId:
            raise HTTPException(status_code=403, detail="API key does not match agent")
        safe_address = _get_safe_address(agent.wallet_address)
        eoa_address = agent.wallet_address
        agent_id = req.agentId
    else:
        raise HTTPException(status_code=400, detail="Provide either safeAddress or agentId")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BRIDGE_BASE}/deposit",
            json={"address": safe_address},
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Bridge API error: {resp.text}",
            )
        data = resp.json()

    raw_addresses = data.get("address", {})

    # Annotate each address type with which chains it supports
    deposit_addresses = {
        addr_type: {
            "address": addr_val,
            "supportedChains": ADDRESS_TYPE_CHAINS.get(addr_type, []),
            "tip": f"Use this address when sending from {', '.join(ADDRESS_TYPE_CHAINS.get(addr_type, [addr_type]))}",
        }
        for addr_type, addr_val in raw_addresses.items()
    }

    result = {
        "safeAddress": safe_address,
        "depositAddresses": deposit_addresses,
        "note": "Funds bridge to USDC.e on your Polygon Safe wallet automatically.",
        "forBase": deposit_addresses.get("evm", {}).get("address", "evm address not returned"),
    }
    if agent_id:
        result["agentId"] = agent_id
    if eoa_address:
        result["eoaAddress"] = eoa_address

    return result


@router.post("/quote")
async def get_bridge_quote(req: QuoteRequest):
    """Get a bridge quote for cross-chain deposit.

    Shows estimated output, fees, gas costs, and time for bridging
    tokens from another chain to USDC.e on Polygon.

    Example: Bridge 10 USDC from Ethereum to Polygon
    ```json
    {
      "fromAmountBaseUnit": "10000000",
      "fromChainId": "1",
      "fromTokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    }
    ```
    """
    # Need a recipient address for the quote — use a placeholder
    # The actual deposit will use the agent's wallet address
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BRIDGE_BASE}/quote",
            json={
                "fromAmountBaseUnit": req.fromAmountBaseUnit,
                "fromChainId": req.fromChainId,
                "fromTokenAddress": req.fromTokenAddress,
                "recipientAddress": "0x0000000000000000000000000000000000000000",
                "toChainId": req.toChainId,
                "toTokenAddress": req.toTokenAddress,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Quote error: {resp.text}",
            )

    return resp.json()


@router.get("/info")
async def deposit_info():
    """Quick reference for funding your agent wallet.

    Returns key addresses, supported methods, and important notes
    about USDC.e vs USDC on Polygon.
    """
    return {
        "methods": [
            {
                "method": "Direct transfer on Polygon",
                "token": "USDC.e (Bridged USDC)",
                "address": USDC_E_POLYGON,
                "note": "Send USDC.e directly to your agent's wallet address on Polygon. Do NOT send native USDC.",
            },
            {
                "method": "Cross-chain bridge",
                "description": "Send from Ethereum, Arbitrum, Base, Solana, or Bitcoin",
                "steps": [
                    "1. Call POST /deposit/address with your agentId",
                    "2. Send tokens to the returned deposit address for your source chain",
                    "3. Tokens are automatically bridged to USDC.e on Polygon",
                ],
            },
        ],
        "important": {
            "usdc_e": {
                "name": "USDC.e (Bridged USDC)",
                "address": USDC_E_POLYGON,
                "chainId": "137",
                "decimals": 6,
                "note": "This is what Polymarket uses. Always send USDC.e, not native USDC.",
            },
            "usdc_native": {
                "name": "USDC (Native)",
                "address": USDC_NATIVE_POLYGON,
                "chainId": "137",
                "decimals": 6,
                "note": "DO NOT send this to Polymarket. It will not work for trading.",
            },
        },
        "minimum_deposit_usd": 45,
    }
