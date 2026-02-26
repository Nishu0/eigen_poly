"""Trade route — real on-chain trade execution via split + CLOB sell.

Signs transactions with the server wallet (POLYCLAW_PRIVATE_KEY),
authenticated via the agent's API key. Records trades and positions in PostgreSQL.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.wallet_manager import WalletManager
from lib.gamma_client import GammaClient
from lib.position_storage import PositionStorage, PositionEntry, TradeStorage

# Import the real trade executor from scripts
from scripts.trade import TradeExecutor


router = APIRouter()
store = AgentStore()
positions = PositionStorage()
trades = TradeStorage()


class RiskConfig(BaseModel):
    maxSlippage: float = 0.05
    maxPositionPct: float = 0.10


class TradeRequest(BaseModel):
    agentId: str
    marketId: str
    side: str  # YES or NO
    amountUsd: float
    skipClobSell: bool = False
    riskConfig: Optional[RiskConfig] = None


class TradeResponse(BaseModel):
    status: str
    tradeId: str
    market: str
    marketId: str
    side: str
    amountUsd: float
    entryPrice: float
    splitTx: Optional[str]
    clobOrderId: Optional[str]
    clobFilled: bool
    positionId: Optional[str]
    error: Optional[str]


@router.post("/trade", response_model=TradeResponse)
async def execute_trade(req: TradeRequest, api_key: str = Depends(require_api_key)):
    """Execute a real on-chain trade: split USDC into YES+NO, sell unwanted via CLOB.

    Signs transactions with the server wallet (POLYCLAW_PRIVATE_KEY).
    Requires a valid agent API key. Records trade + position in PostgreSQL.
    """

    # 1. Verify API key ownership
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != req.agentId:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    # 2. Validate inputs
    side = req.side.upper()
    if side not in ("YES", "NO"):
        raise HTTPException(status_code=400, detail="side must be YES or NO")

    if req.amountUsd <= 0:
        raise HTTPException(status_code=400, detail="amountUsd must be positive")

    # 3. Initialize wallet from server env
    wallet = WalletManager()
    if not wallet.is_unlocked:
        raise HTTPException(
            status_code=503,
            detail="Server wallet not configured. Set POLYCLAW_PRIVATE_KEY in .env",
        )

    # 4. Pre-flight: check slippage against live market price
    risk = req.riskConfig or RiskConfig()
    gamma = GammaClient()
    try:
        market = await gamma.get_market(req.marketId)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Market not found: {req.marketId}")

    if market.closed or market.resolved:
        raise HTTPException(status_code=400, detail="Market is closed or resolved")

    entry_price = market.yes_price if side == "YES" else market.no_price
    if entry_price > (1 - risk.maxSlippage):
        raise HTTPException(
            status_code=400,
            detail=f"Price {entry_price:.4f} exceeds slippage limit (max: {1 - risk.maxSlippage})",
        )

    # 5. Execute the real trade — split on-chain + CLOB sell
    executor = TradeExecutor(wallet)
    try:
        result = await executor.buy_position(
            market_id=req.marketId,
            position=side,
            amount=req.amountUsd,
            skip_clob_sell=req.skipClobSell,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {e}")
    finally:
        wallet.lock()

    # 6. Generate trade ID
    trade_id = f"trd_{uuid.uuid4().hex[:16]}"

    # 7. Record trade in DB
    await trades.record(
        trade_id=trade_id,
        agent_id=req.agentId,
        market_id=req.marketId,
        question=result.question,
        side=side,
        amount_usd=req.amountUsd,
        entry_price=result.entry_price,
        split_tx=result.split_tx,
        clob_order_id=result.clob_order_id,
        clob_filled=result.clob_filled,
        status="executed" if result.success else "failed",
        error=result.error,
    )

    # 8. Record position if split succeeded
    position_id = None
    if result.success:
        position_id = str(uuid.uuid4())
        entry = PositionEntry(
            position_id=position_id,
            agent_id=req.agentId,
            market_id=result.market_id,
            question=result.question,
            position=result.position,
            token_id=result.wanted_token_id,
            entry_time=datetime.now(timezone.utc).isoformat(),
            entry_amount=result.amount,
            entry_price=result.entry_price,
            split_tx=result.split_tx,
            clob_order_id=result.clob_order_id,
            clob_filled=result.clob_filled,
        )
        await positions.add(entry)

    # 9. Return result
    return TradeResponse(
        status="executed" if result.success else "failed",
        tradeId=trade_id,
        market=result.question,
        marketId=req.marketId,
        side=side,
        amountUsd=req.amountUsd,
        entryPrice=result.entry_price,
        splitTx=result.split_tx,
        clobOrderId=result.clob_order_id,
        clobFilled=result.clob_filled,
        positionId=position_id,
        error=result.error,
    )
