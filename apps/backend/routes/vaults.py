"""Vaults route — USDC yield vault discovery on Base.

Checks Fluid, Aave v3, Compound v3, Euler, and Morpho USDC vaults on Base
using DeFi Llama yields API. No auth required — public data.

Used by the auto_rebalance cron to find the best place to park idle USDC.
"""

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/vaults", tags=["Vaults"])

DEFILLAMA_YIELDS = "https://yields.llama.fi/pools"

# protocols we track on Base
TRACKED_PROTOCOLS = {
    "aave-v3":    "Aave v3",
    "compound-v3": "Compound v3",
    "euler":       "Euler",
    "morpho":      "Morpho",
    "fluid":       "Fluid",
}


class VaultInfo(BaseModel):
    protocol: str
    protocol_slug: str
    pool_id: str
    symbol: str
    chain: str
    apy: float          # total APY (base + rewards)
    apy_base: float
    apy_reward: float
    tvl_usd: float
    il_risk: str        # "none" for single-asset USDC vaults
    url: Optional[str] = None


class VaultsResponse(BaseModel):
    chain: str
    vaults: list[VaultInfo]
    best_apy: float
    best_protocol: str
    total_checked: int


@router.get("/base", response_model=VaultsResponse)
async def get_base_vaults(
    min_tvl: float = Query(default=1_000_000, description="minimum TVL in USD"),
    min_apy: float = Query(default=0.0, description="minimum APY filter"),
):
    """
    current USDC vault yields on Base across Fluid, Aave v3, Compound v3, Euler, Morpho.

    sorted by total APY descending. used by the auto_rebalance feature to find
    the best yield for idle USDC (giza protocol targets 15%, these range 2-8%).
    """
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(DEFILLAMA_YIELDS)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="defillama yields api unavailable")
            all_pools = resp.json().get("data", [])
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="defillama api timed out")

    vaults: list[VaultInfo] = []

    for pool in all_pools:
        chain = (pool.get("chain") or "").lower()
        project = (pool.get("project") or "").lower()
        symbol = (pool.get("symbol") or "").upper()

        if chain != "base":
            continue
        if project not in TRACKED_PROTOCOLS:
            continue
        if "USDC" not in symbol:
            continue

        tvl = pool.get("tvlUsd") or 0
        apy = pool.get("apy") or 0
        apy_base = pool.get("apyBase") or 0
        apy_reward = pool.get("apyReward") or 0

        if tvl < min_tvl or apy < min_apy:
            continue

        vaults.append(VaultInfo(
            protocol=TRACKED_PROTOCOLS[project],
            protocol_slug=project,
            pool_id=pool.get("pool", ""),
            symbol=symbol,
            chain="base",
            apy=round(apy, 4),
            apy_base=round(apy_base, 4),
            apy_reward=round(apy_reward, 4),
            tvl_usd=round(tvl, 2),
            il_risk="none",
            url=pool.get("url"),
        ))

    vaults.sort(key=lambda v: v.apy, reverse=True)

    best = vaults[0] if vaults else None

    return VaultsResponse(
        chain="base",
        vaults=vaults,
        best_apy=best.apy if best else 0.0,
        best_protocol=best.protocol if best else "none",
        total_checked=len(vaults),
    )
