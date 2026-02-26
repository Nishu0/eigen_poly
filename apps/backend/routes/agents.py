"""Agent routes — positions, trade history, and PnL."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.position_storage import PositionStorage, TradeStorage
from lib.gamma_client import GammaClient


router = APIRouter()
store = AgentStore()
positions = PositionStorage()
trades = TradeStorage()
gamma = GammaClient()


class PositionOut(BaseModel):
    position_id: str
    market_id: str
    question: str
    position: str
    token_id: Optional[str]
    entry_amount: Optional[float]
    entry_price: Optional[float]
    current_price: Optional[float]
    pnl_usd: Optional[float]
    pnl_pct: Optional[float]
    status: str
    created_at: Optional[str]


class TradeOut(BaseModel):
    trade_id: str
    market_id: str
    question: Optional[str]
    side: str
    amount_usd: float
    entry_price: Optional[float]
    split_tx: Optional[str]
    clob_order_id: Optional[str]
    clob_filled: Optional[bool]
    status: str
    error: Optional[str]
    created_at: Optional[str]


class PnLSummary(BaseModel):
    agentId: str
    total_invested: float
    total_current_value: float
    total_pnl_usd: float
    total_pnl_pct: float
    open_positions: int
    total_trades: int


@router.get("/agents/{agent_id}/positions", response_model=list[PositionOut])
async def get_agent_positions(agent_id: str, api_key: str = Depends(require_api_key)):
    """Get all positions for an agent with live P&L."""

    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    rows = await positions.get_by_agent(agent_id)
    results = []

    for row in rows:
        current_price = None
        pnl_usd = None
        pnl_pct = None

        # Fetch live price for open positions
        if row.get("status") == "open" and row.get("token_id"):
            try:
                prices = await gamma.get_prices([row["token_id"]])
                if row["token_id"] in prices:
                    current_price = float(prices[row["token_id"]])
                    entry = row.get("entry_price", 0) or 0
                    amount = row.get("entry_amount", 0) or 0
                    if entry > 0 and amount > 0:
                        tokens = amount / entry
                        current_value = tokens * current_price
                        pnl_usd = round(current_value - amount, 2)
                        pnl_pct = round((pnl_usd / amount) * 100, 2)
            except Exception:
                pass

        results.append(PositionOut(
            position_id=row["position_id"],
            market_id=row["market_id"],
            question=row.get("question", ""),
            position=row["position"],
            token_id=row.get("token_id"),
            entry_amount=row.get("entry_amount"),
            entry_price=row.get("entry_price"),
            current_price=current_price,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            status=row.get("status", "open"),
            created_at=str(row.get("created_at", "")),
        ))

    return results


@router.get("/agents/{agent_id}/trades", response_model=list[TradeOut])
async def get_agent_trades(
    agent_id: str,
    limit: int = Query(50, ge=1, le=200),
    api_key: str = Depends(require_api_key),
):
    """Get trade history for an agent."""

    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    rows = await trades.get_by_agent(agent_id, limit=limit)

    return [
        TradeOut(
            trade_id=r["trade_id"],
            market_id=r["market_id"],
            question=r.get("question"),
            side=r["side"],
            amount_usd=r["amount_usd"],
            entry_price=r.get("entry_price"),
            split_tx=r.get("split_tx"),
            clob_order_id=r.get("clob_order_id"),
            clob_filled=r.get("clob_filled"),
            status=r.get("status", "executed"),
            error=r.get("error"),
            created_at=str(r.get("created_at", "")),
        )
        for r in rows
    ]


@router.get("/agents/{agent_id}/pnl", response_model=PnLSummary)
async def get_agent_pnl(agent_id: str, api_key: str = Depends(require_api_key)):
    """Get P&L summary for an agent."""

    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    pos_rows = await positions.get_by_agent(agent_id)
    trade_rows = await trades.get_by_agent(agent_id)

    total_invested = 0.0
    total_current = 0.0
    open_count = 0

    for row in pos_rows:
        entry = row.get("entry_price", 0) or 0
        amount = row.get("entry_amount", 0) or 0
        total_invested += amount

        if row.get("status") == "open" and row.get("token_id") and entry > 0:
            open_count += 1
            try:
                prices = await gamma.get_prices([row["token_id"]])
                if row["token_id"] in prices:
                    current_price = float(prices[row["token_id"]])
                    tokens = amount / entry
                    total_current += tokens * current_price
                else:
                    total_current += amount  # Fallback to entry
            except Exception:
                total_current += amount
        else:
            total_current += amount

    pnl_usd = round(total_current - total_invested, 2)
    pnl_pct = round((pnl_usd / total_invested) * 100, 2) if total_invested > 0 else 0.0

    return PnLSummary(
        agentId=agent_id,
        total_invested=round(total_invested, 2),
        total_current_value=round(total_current, 2),
        total_pnl_usd=pnl_usd,
        total_pnl_pct=pnl_pct,
        open_positions=open_count,
        total_trades=len(trade_rows),
    )
