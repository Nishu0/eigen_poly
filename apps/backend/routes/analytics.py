"""Analytics proxy routes — proxies to Sozu (polymarket-analytics) without exposing the upstream URL."""

import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/analytics", tags=["Analytics"])

SOZU_BASE = os.environ.get(
    "SOZU_BASE_URL", "https://polymarket-analytics.bk.osirislabs.xyz"
)

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=15.0)
    return _client


async def _proxy_get(path: str, params: dict) -> dict:
    """Forward a GET request to Sozu and return the JSON response."""
    # Strip out None/empty params
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    try:
        resp = await _get_client().get(f"{SOZU_BASE}{path}", params=clean)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


async def _proxy_post(path: str) -> dict:
    """Forward a POST request to Sozu and return the JSON response."""
    try:
        resp = await _get_client().post(f"{SOZU_BASE}{path}")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


# ── Opportunities ────────────────────────────────────────────────────────────


@router.get("/opportunities")
async def list_opportunities(
    strategy: Optional[str] = None,
    minScore: Optional[float] = None,
    limit: Optional[int] = Query(default=20, le=100),
    status: Optional[str] = None,
):
    """List trading opportunities from Polymarket Analytics."""
    return await _proxy_get(
        "/api/opportunities",
        {"strategy": strategy, "minScore": minScore, "limit": limit, "status": status},
    )


@router.get("/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: int):
    """Get a single trading opportunity by ID."""
    return await _proxy_get(f"/api/opportunities/{opportunity_id}", {})


@router.post("/opportunities/{opportunity_id}/acknowledge")
async def acknowledge_opportunity(opportunity_id: int):
    """Dismiss / acknowledge a trading opportunity."""
    return await _proxy_post(f"/api/opportunities/{opportunity_id}/acknowledge")


# ── Wallets ──────────────────────────────────────────────────────────────────


@router.get("/wallets")
async def list_wallets(
    limit: Optional[int] = Query(default=20, le=100),
    sortBy: Optional[str] = None,
    sortOrder: Optional[str] = None,
    cursor: Optional[str] = None,
):
    """List top Polymarket wallets with performance stats."""
    return await _proxy_get(
        "/api/wallets",
        {"limit": limit, "sortBy": sortBy, "sortOrder": sortOrder, "cursor": cursor},
    )


@router.get("/wallets/{address}/analyze")
async def analyze_wallet(address: str):
    """Deep analytics for a specific wallet address (PnL, win rate, smart score)."""
    return await _proxy_get(f"/api/wallets/{address}/analyze", {})
