from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from market_clients import fetch_all_markets, fetch_gnosis_markets, fetch_polymarket_markets
from strategies.arbitrage import build_arbitrage_plans

app = FastAPI(title="EigenPoly Strategy Bridge")


class ArbitrageRequest(BaseModel):
    limit: int = 50
    total_trade_amount: float = 10.0
    min_profit: float = 0.005


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/markets/polymarket")
def markets_polymarket(limit: int = 50) -> dict:
    return {"ok": True, "markets": [m.model_dump() for m in fetch_polymarket_markets(limit=limit)]}


@app.get("/markets/gnosis")
def markets_gnosis(limit: int = 50) -> dict:
    return {"ok": True, "markets": [m.model_dump() for m in fetch_gnosis_markets(limit=limit)]}


@app.get("/markets/unified")
def markets_unified(limit: int = 50) -> dict:
    return {"ok": True, "markets": [m.model_dump() for m in fetch_all_markets(limit=limit)]}


@app.post("/strategies/arbitrage/plan")
def strategy_arbitrage_plan(req: ArbitrageRequest) -> dict:
    plans = build_arbitrage_plans(
        limit=req.limit,
        total_trade_amount=req.total_trade_amount,
        min_profit=req.min_profit,
    )
    return {"ok": True, "plans": [p.model_dump() for p in plans]}
