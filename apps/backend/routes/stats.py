"""Public stats endpoint — no auth required."""

from fastapi import APIRouter
from lib.database import get_pool

router = APIRouter()


@router.get("/stats")
async def get_stats():
    """Return platform-level stats: agent count, trade count, volume, positions."""
    pool = get_pool()
    async with pool.acquire() as conn:
        agent_count = await conn.fetchval("SELECT COUNT(*) FROM agents") or 0
        trade_count = await conn.fetchval("SELECT COUNT(*) FROM trades WHERE status = 'executed'") or 0
        trade_volume = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_usd), 0) FROM trades WHERE status = 'executed'"
        ) or 0.0
        open_positions = await conn.fetchval(
            "SELECT COUNT(*) FROM positions WHERE status = 'open'"
        ) or 0

    return {
        "agents": int(agent_count),
        "trades": int(trade_count),
        "volume_usd": round(float(trade_volume), 2),
        "open_positions": int(open_positions),
    }
