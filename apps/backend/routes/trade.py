"""Trade route — market-aware trade execution for agents."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.gamma_client import GammaClient


router = APIRouter()
store = AgentStore()
gamma = GammaClient()


class RiskConfig(BaseModel):
    maxSlippage: float = 0.05
    maxPositionPct: float = 0.10


class TradeRequest(BaseModel):
    agentId: str
    marketId: str
    side: str  # YES or NO
    amountUsd: float
    riskConfig: Optional[RiskConfig] = None


class TradeResponse(BaseModel):
    status: str
    tradeId: str
    market: str
    marketId: str
    side: str
    amountUsd: float
    entryPrice: float
    tokensReceived: float
    executionProof: str
    postTradeBalance: dict


@router.post("/trade", response_model=TradeResponse)
async def execute_trade(req: TradeRequest, api_key: str = Depends(require_api_key)):
    """Execute a market-aware trade for a registered agent."""

    # Verify API key ownership
    key_hash = hash_api_key(api_key)
    agent = store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != req.agentId:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    # Validate side
    if req.side.upper() not in ("YES", "NO"):
        raise HTTPException(status_code=400, detail="side must be YES or NO")

    # Validate amount
    if req.amountUsd <= 0:
        raise HTTPException(status_code=400, detail="amountUsd must be positive")

    # Fetch market from Polymarket to validate it exists
    try:
        market = await gamma.get_market(req.marketId)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Market not found: {req.marketId}")

    if market.closed or market.resolved:
        raise HTTPException(status_code=400, detail="Market is closed or resolved")

    # Get entry price from market data
    entry_price = market.yes_price if req.side.upper() == "YES" else market.no_price

    # Check slippage constraints
    risk = req.riskConfig or RiskConfig()
    if entry_price > (1 - risk.maxSlippage):
        raise HTTPException(
            status_code=400,
            detail=f"Price {entry_price} exceeds slippage limit (max acceptable: {1 - risk.maxSlippage})",
        )

    # Calculate expected tokens
    tokens_received = req.amountUsd / entry_price if entry_price > 0 else 0

    # Generate trade ID and execution proof
    trade_id = f"trd_{uuid.uuid4().hex[:16]}"
    execution_proof = f"eigen_compute_{uuid.uuid4().hex[:12]}"

    # TODO: In production, this would:
    # 1. Run policy/risk checks via Eigen Compute
    # 2. Execute split + CLOB via Polygon Safe
    # 3. Optionally rebalance to Solana vault
    # 4. Record receipt and PnL delta

    return TradeResponse(
        status="executed",
        tradeId=trade_id,
        market=market.question,
        marketId=req.marketId,
        side=req.side.upper(),
        amountUsd=req.amountUsd,
        entryPrice=entry_price,
        tokensReceived=round(tokens_received, 4),
        executionProof=execution_proof,
        postTradeBalance={"usdc_e": 0.0},  # Placeholder — would come from WalletManager
    )
