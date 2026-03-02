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
