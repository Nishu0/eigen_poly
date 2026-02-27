"""Deposit routes — Polymarket Bridge API proxy.

Provides cross-chain deposit addresses, supported assets list,
and bridge quotes for funding agent wallets.

Bridge API base: https://bridge.polymarket.com
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore

router = APIRouter(prefix="/deposit", tags=["deposit"])
store = AgentStore()

BRIDGE_BASE = "https://bridge.polymarket.com"

# USDC.e on Polygon — this is what Polymarket Safe uses, NOT native USDC
USDC_E_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_NATIVE_POLYGON = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"


# --- Models ---


class DepositAddressRequest(BaseModel):
    agentId: str


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
    api_key: str = Depends(require_api_key),
):
    """Create cross-chain deposit addresses for an agent's wallet.

    Returns deposit addresses for:
    - **EVM** (Ethereum, Polygon, Arbitrum, Base, etc.)
    - **Solana** (SVM)
    - **Bitcoin** (BTC)

    Send supported tokens to these addresses — they'll be automatically
    bridged and converted to USDC.e on Polygon in the agent's wallet.
    """
    # Verify ownership
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != req.agentId:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    # Call Polymarket Bridge API
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BRIDGE_BASE}/deposit",
            json={"address": agent.wallet_address},
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Bridge API error: {resp.text}",
            )
        data = resp.json()

    return {
        "agentId": req.agentId,
        "walletAddress": agent.wallet_address,
        "depositAddresses": data.get("address", {}),
        "note": data.get("note", "Only certain chains and tokens are supported. See /deposit/supported-assets."),
        "_tip": "Send supported tokens to these addresses. They'll be bridged to USDC.e on Polygon automatically.",
    }


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
