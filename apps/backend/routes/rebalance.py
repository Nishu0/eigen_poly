"""Rebalance routes — vault position, logs, earnings, manual trigger."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from lib.agent_store import AgentStore
from lib.auth import hash_api_key, require_api_key
from lib.database import get_pool
from lib.rebalance import (
    _env,
    _get_active_position,
    get_position_current_value,
    run_rebalance_for_agent,
)

router = APIRouter(prefix="/rebalance", tags=["Rebalance"])
store = AgentStore()


async def _auth_agent(agent_id: str, api_key: str):
    """Verify the API key belongs to the requested agent_id."""
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")
    return agent


@router.get("/{agent_id}/position")
async def get_vault_position(agent_id: str, api_key: str = Depends(require_api_key)):
    """Current active vault position with live on-chain value and estimated earnings.

    Returns where the money is, what APY it's earning, and how much it's made so far.
    """
    agent = await _auth_agent(agent_id, api_key)
    position = await _get_active_position(agent_id)

    if not position:
        return {
            "invested": False,
            "agent_id": agent_id,
            "message": "No active vault position. Enable auto_rebalance flag to start.",
        }

    now = datetime.now(timezone.utc)
    deposited_at = position["deposited_at"]
    if deposited_at.tzinfo is None:
        deposited_at = deposited_at.replace(tzinfo=timezone.utc)
    days = (now - deposited_at).total_seconds() / 86400
    apy = position["apy_at_entry"]

    # Live on-chain value
    current_value = await get_position_current_value(dict(position))

    # Earnings calculations
    deposited = position["amount_usdc"]
    estimated_earnings = round(deposited * (apy / 100) * (days / 365), 4)
    exact_earnings = round(current_value - deposited, 4)

    return {
        "invested": True,
        "agent_id": agent_id,
        "position_id": position["position_id"],
        "protocol": position["protocol_name"],
        "protocol_slug": position["protocol"],
        "pool_id": position["pool_id"],
        "amount_deposited": deposited,
        "current_value": round(current_value, 6),
        "earnings_usdc": exact_earnings if exact_earnings > 0 else estimated_earnings,
        "earnings_pct": round((exact_earnings / deposited) * 100, 4) if deposited > 0 else 0,
        "apy": apy,
        "days_invested": round(days, 2),
        "deposited_at": deposited_at.isoformat(),
        "deposit_tx": position.get("deposit_tx"),
    }


@router.get("/{agent_id}/logs")
async def get_rebalance_logs(
    agent_id: str,
    limit: int = Query(50, ge=1, le=200),
    api_key: str = Depends(require_api_key),
):
    """Full history of rebalance actions — deposits, withdrawals, skips, errors.

    Shows where money was, when it moved, what APY triggered the move.
    """
    await _auth_agent(agent_id, api_key)
    db = get_pool()
    rows = await db.fetch(
        "SELECT * FROM vault_logs WHERE agent_id=$1 ORDER BY created_at DESC LIMIT $2",
        agent_id,
        limit,
    )
    return [dict(r) for r in rows]


@router.get("/{agent_id}/summary")
async def get_rebalance_summary(agent_id: str, api_key: str = Depends(require_api_key)):
    """One-line dashboard summary — ideal for the agent page idle money card.

    Shows current position, earnings, idle USDC, and next check time.
    """
    agent = await _auth_agent(agent_id, api_key)
    position = await _get_active_position(agent_id)
    db = get_pool()

    # Last log entry
    last_log = await db.fetchrow(
        "SELECT * FROM vault_logs WHERE agent_id=$1 ORDER BY created_at DESC LIMIT 1",
        agent_id,
    )

    interval_hours = int(_env("REBALANCE_INTERVAL_HOURS", "3"))

    if not position:
        return {
            "invested": False,
            "auto_rebalance": agent.auto_rebalance,
            "idle_usdc": None,
            "last_checked": last_log["created_at"].isoformat() if last_log else None,
            "interval_hours": interval_hours,
            "message": "No active position"
            + ("" if agent.auto_rebalance else " — enable auto_rebalance to start"),
        }

    now = datetime.now(timezone.utc)
    deposited_at = position["deposited_at"]
    if deposited_at.tzinfo is None:
        deposited_at = deposited_at.replace(tzinfo=timezone.utc)
    days = (now - deposited_at).total_seconds() / 86400
    apy = position["apy_at_entry"]
    deposited = position["amount_usdc"]
    current_value = await get_position_current_value(dict(position))
    earnings = round(current_value - deposited, 4)

    last_checked = last_log["created_at"].isoformat() if last_log else None

    return {
        "invested": True,
        "auto_rebalance": agent.auto_rebalance,
        "protocol": position["protocol_name"],
        "amount_usdc": deposited,
        "current_value": round(current_value, 4),
        "earnings_usdc": earnings if earnings > 0 else round(deposited * (apy / 100) * (days / 365), 4),
        "apy": apy,
        "days_invested": round(days, 2),
        "deposited_at": deposited_at.isoformat(),
        "last_checked": last_checked,
        "interval_hours": interval_hours,
    }


@router.post("/{agent_id}/trigger")
async def trigger_rebalance(agent_id: str, api_key: str = Depends(require_api_key)):
    """Manually trigger a rebalance check for this agent.

    Useful for testing. Runs the full rebalance cycle synchronously and returns the result.
    Warning: may take 30-120 seconds if transactions are submitted.
    """
    agent = await _auth_agent(agent_id, api_key)
    result = await run_rebalance_for_agent(agent)
    return result
