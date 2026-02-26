"""Market routes — fetch and analyze Polymarket data."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib.gamma_client import GammaClient


router = APIRouter()
gamma = GammaClient()


class MarketOut(BaseModel):
    id: str
    question: str
    slug: str
    condition_id: str
    yes_token_id: str
    no_token_id: str | None
    yes_price: float
    no_price: float
    volume: float
    volume_24h: float
    liquidity: float
    end_date: str
    active: bool
    closed: bool
    resolved: bool
    outcome: str | None


class MarketAnalysis(BaseModel):
    id: str
    question: str
    yes_price: float
    no_price: float
    volume_24h: float
    liquidity: float
    spread: float
    liquidity_score: str
    opportunity_signal: str


class AnalysisResponse(BaseModel):
    count: int
    markets: list[MarketAnalysis]


def _market_to_out(m) -> MarketOut:
    return MarketOut(**asdict(m))


def _analyze_market(m) -> MarketAnalysis:
    """Compute basic analysis signals for a market."""
    spread = abs(m.yes_price - (1 - m.no_price))

    # Liquidity score
    if m.liquidity >= 100_000:
        liq_score = "HIGH"
    elif m.liquidity >= 10_000:
        liq_score = "MEDIUM"
    else:
        liq_score = "LOW"

    # Opportunity signal based on spread and volume
    if spread > 0.05 and m.volume_24h > 50_000:
        signal = "STRONG"
    elif spread > 0.02 and m.volume_24h > 10_000:
        signal = "MODERATE"
    elif m.volume_24h > 100_000:
        signal = "VOLUME_SPIKE"
    else:
        signal = "NEUTRAL"

    return MarketAnalysis(
        id=m.id,
        question=m.question,
        yes_price=m.yes_price,
        no_price=m.no_price,
        volume_24h=m.volume_24h,
        liquidity=m.liquidity,
        spread=round(spread, 4),
        liquidity_score=liq_score,
        opportunity_signal=signal,
    )


@router.get("/markets/trending", response_model=list[MarketOut])
async def trending_markets(limit: int = Query(20, ge=1, le=100)):
    """Fetch trending Polymarket markets by 24h volume."""
    try:
        markets = await gamma.get_trending_markets(limit=limit)
        return [_market_to_out(m) for m in markets]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch markets: {e}")


@router.get("/markets/search", response_model=list[MarketOut])
async def search_markets(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    """Search Polymarket markets by keyword."""
    try:
        markets = await gamma.search_markets(query=q, limit=limit)
        return [_market_to_out(m) for m in markets]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market search failed: {e}")


@router.get("/markets/analysis", response_model=AnalysisResponse)
async def market_analysis(limit: int = Query(10, ge=1, le=50)):
    """Aggregate market analysis — volume, liquidity, spread, opportunity signals."""
    try:
        markets = await gamma.get_trending_markets(limit=limit)
        analyses = [_analyze_market(m) for m in markets]
        return AnalysisResponse(count=len(analyses), markets=analyses)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.get("/markets/{market_id}", response_model=MarketOut)
async def get_market(market_id: str):
    """Get full details for a single Polymarket market."""
    try:
        market = await gamma.get_market(market_id)
        return _market_to_out(market)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Market not found: {market_id}")
