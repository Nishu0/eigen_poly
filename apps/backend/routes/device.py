"""Device code flow — agent claim via human authorization.

Implements RFC 8628-style device flow:
1. Agent registers → gets device_code + user_code (claim code)
2. Human opens /device?code=XXXX-YYYY → logs in → authorizes
3. Agent polls /device/poll → gets confirmation
"""

import secrets
import string
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lib.database import get_pool
from routes.oauth import get_current_user


router = APIRouter(tags=["Device Flow"])

DEVICE_CODE_EXPIRY_SECONDS = 900  # 15 minutes


def _generate_user_code() -> str:
    """Generate a short human-readable code like ABCD-1234."""
    letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{letters}-{digits}"


def _generate_device_code() -> str:
    """Generate a long random device code for polling."""
    return f"dc_{secrets.token_hex(24)}"


async def create_device_code(agent_id: str) -> dict:
    """Create a device code for an agent. Called during registration."""
    pool = get_pool()

    device_code = _generate_device_code()
    user_code = _generate_user_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=DEVICE_CODE_EXPIRY_SECONDS)

    await pool.execute(
        """INSERT INTO device_codes (device_code, user_code, agent_id, status, expires_at)
           VALUES ($1, $2, $3, 'pending', $4)""",
        device_code, user_code, agent_id, expires_at,
    )

    return {
        "deviceCode": device_code,
        "userCode": user_code,
        "expiresIn": DEVICE_CODE_EXPIRY_SECONDS,
        "interval": 5,
    }


# --- Routes ---


@router.get("/device/{code}")
async def get_device_info(code: str):
    """Get device code info for the claim page.

    The frontend calls this to show the agent name and permissions.
    """
    pool = get_pool()

    # Look up by user_code
    row = await pool.fetchrow(
        """SELECT dc.*, a.agent_id, a.wallet_address, a.scopes, a.created_at as agent_created
           FROM device_codes dc
           JOIN agents a ON dc.agent_id = a.agent_id
           WHERE dc.user_code = $1""",
        code.upper(),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Invalid or expired claim code")

    if row["status"] != "pending":
        return {
            "status": row["status"],
            "agentId": row["agent_id"],
            "message": f"This code has already been {row['status']}.",
        }

    if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await pool.execute(
            "UPDATE device_codes SET status = 'expired' WHERE user_code = $1", code.upper()
        )
        raise HTTPException(status_code=410, detail="Claim code has expired")

    return {
        "status": "pending",
        "agentId": row["agent_id"],
        "walletAddress": row["wallet_address"],
        "scopes": list(row["scopes"]) if row["scopes"] else [],
        "createdAt": row["agent_created"].isoformat() if row["agent_created"] else "",
        "permissions": [
            "View wallet balances",
            "Place trades on Polymarket",
            "Sign on-chain transactions",
        ],
    }


class AuthorizeRequest(BaseModel):
    code: str


@router.post("/device/authorize")
async def authorize_device(req: AuthorizeRequest, request: Request):
    """Authorize an agent claim — link agent to the logged-in user.

    Requires a valid session cookie (Google OAuth login).
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required to authorize")

    pool = get_pool()
    user_id = user["sub"]

    # Get the device code
    row = await pool.fetchrow(
        "SELECT * FROM device_codes WHERE user_code = $1", req.code.upper()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invalid claim code")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Code already {row['status']}")
    if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Code expired")

    agent_id = row["agent_id"]

    # Link agent to user
    await pool.execute(
        "UPDATE agents SET owner_id = $1 WHERE agent_id = $2", user_id, agent_id
    )

    # Mark device code as authorized
    await pool.execute(
        "UPDATE device_codes SET status = 'authorized', user_id = $1 WHERE user_code = $2",
        user_id, req.code.upper(),
    )

    return {
        "status": "authorized",
        "agentId": agent_id,
        "message": "Agent successfully linked to your account!",
    }


@router.post("/device/deny")
async def deny_device(req: AuthorizeRequest, request: Request):
    """Deny an agent claim."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")

    pool = get_pool()
    await pool.execute(
        "UPDATE device_codes SET status = 'denied' WHERE user_code = $1", req.code.upper()
    )
    return {"status": "denied", "message": "Agent claim denied."}


class PollRequest(BaseModel):
    deviceCode: str


@router.post("/device/poll")
async def poll_device(req: PollRequest):
    """Agent polls for authorization status.

    Returns:
    - pending: keep polling
    - authorized: agent is linked, proceed
    - denied: user rejected
    - expired: code timed out
    """
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM device_codes WHERE device_code = $1", req.deviceCode
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invalid device code")

    # Check expiry
    if row["status"] == "pending" and row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await pool.execute(
            "UPDATE device_codes SET status = 'expired' WHERE device_code = $1", req.deviceCode
        )
        return {"status": "expired"}

    return {
        "status": row["status"],
        "agentId": row["agent_id"],
    }


@router.get("/user/agents")
async def get_user_agents(request: Request):
    """Get all agents owned by the logged-in user, including last 5 trades each."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")

    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM agents WHERE owner_id = $1 ORDER BY created_at DESC",
        user["sub"],
    )

    agents = []
    for r in rows:
        agent_id = r["agent_id"]

        # Fetch last 5 trades for this agent
        trade_rows = await pool.fetch(
            """SELECT trade_id, market_id, question, side, amount_usd, entry_price,
                      status, clob_filled, split_tx, created_at
               FROM trades
               WHERE agent_id = $1
               ORDER BY created_at DESC
               LIMIT 5""",
            agent_id,
        )

        recent_trades = [
            {
                "trade_id": t["trade_id"],
                "market_id": t["market_id"],
                "question": t.get("question") or "",
                "side": t["side"],
                "amount_usd": float(t["amount_usd"]),
                "entry_price": float(t["entry_price"]) if t.get("entry_price") else None,
                "status": t.get("status", "executed"),
                "clob_filled": bool(t.get("clob_filled", False)),
                "split_tx": t.get("split_tx"),
                "created_at": t["created_at"].isoformat() if t.get("created_at") else "",
            }
            for t in trade_rows
        ]

        agents.append({
            "agentId": agent_id,
            "walletAddress": r["wallet_address"],
            "walletIndex": r.get("wallet_index", 0) or 0,
            "scopes": list(r["scopes"]) if r["scopes"] else [],
            "createdAt": r["created_at"].isoformat() if r["created_at"] else "",
            "recentTrades": recent_trades,
        })

    return {"agents": agents}

