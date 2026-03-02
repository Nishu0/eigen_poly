"""Agent logs routes — view API request history for user's agents."""

from fastapi import APIRouter, Request, HTTPException, Query

from lib.database import get_pool
from routes.oauth import get_current_user


router = APIRouter()


@router.get("/user/logs")
async def get_user_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    agent_id: str | None = Query(None),
):
    """Return API request logs for all agents owned by the logged-in user.

    Supports filtering by agent_id and pagination via limit/offset.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")

    pool = get_pool()
    user_id = user["sub"]

    # Build query — filter to only this user's agents
    if agent_id:
        rows = await pool.fetch(
            """SELECT l.log_id, l.agent_id, l.method, l.path, l.status_code,
                      l.duration_ms, l.ip_address, l.body_snippet, l.created_at
               FROM agent_logs l
               JOIN agents a ON l.agent_id = a.agent_id
               WHERE a.owner_id = $1 AND l.agent_id = $2
               ORDER BY l.created_at DESC
               LIMIT $3 OFFSET $4""",
            user_id, agent_id, limit, offset,
        )
        total = await pool.fetchval(
            """SELECT COUNT(*) FROM agent_logs l
               JOIN agents a ON l.agent_id = a.agent_id
               WHERE a.owner_id = $1 AND l.agent_id = $2""",
            user_id, agent_id,
        )
    else:
        rows = await pool.fetch(
            """SELECT l.log_id, l.agent_id, l.method, l.path, l.status_code,
                      l.duration_ms, l.ip_address, l.body_snippet, l.created_at
               FROM agent_logs l
               JOIN agents a ON l.agent_id = a.agent_id
               WHERE a.owner_id = $1
               ORDER BY l.created_at DESC
               LIMIT $2 OFFSET $3""",
            user_id, limit, offset,
        )
        total = await pool.fetchval(
            """SELECT COUNT(*) FROM agent_logs l
               JOIN agents a ON l.agent_id = a.agent_id
               WHERE a.owner_id = $1""",
            user_id,
        )

    logs = [
        {
            "logId": r["log_id"],
            "agentId": r["agent_id"],
            "method": r["method"],
            "path": r["path"],
            "statusCode": r["status_code"],
            "durationMs": r["duration_ms"],
            "ipAddress": r["ip_address"],
            "bodySnippet": r.get("body_snippet"),
            "createdAt": r["created_at"].isoformat() if r["created_at"] else "",
        }
        for r in rows
    ]

    return {
        "logs": logs,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
    }


@router.get("/user/trades")
async def get_user_trades(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
):
    """Return all trades for agents owned by the logged-in user (most recent first)."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")

    pool = get_pool()
    rows = await pool.fetch(
        """SELECT t.trade_id, t.agent_id, t.market_id, t.question, t.side,
                  t.amount_usd, t.entry_price, t.status, t.clob_filled,
                  t.split_tx, t.created_at
           FROM trades t
           JOIN agents a ON t.agent_id = a.agent_id
           WHERE a.owner_id = $1
           ORDER BY t.created_at DESC
           LIMIT $2""",
        user["sub"], limit,
    )

    return {
        "trades": [
            {
                "trade_id": r["trade_id"],
                "market_id": r["market_id"],
                "question": r.get("question") or "",
                "side": r["side"],
                "amount_usd": float(r["amount_usd"]),
                "entry_price": float(r["entry_price"]) if r.get("entry_price") else None,
                "status": r.get("status", "executed"),
                "clob_filled": bool(r.get("clob_filled", False)),
                "split_tx": r.get("split_tx"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
            }
            for r in rows
        ]
    }
