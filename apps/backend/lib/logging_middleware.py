"""Agent request logging middleware.

Records every API request made with an agent API key into the agent_logs table.
Skips public/OAuth/health routes automatically.
"""

import time
import uuid
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lib.auth import hash_api_key
from lib.database import get_pool


# Paths to skip logging for (no API key involved)
_SKIP_PREFIXES = ("/oauth/", "/health", "/docs", "/openapi", "/device/", "/register")


class AgentLogMiddleware(BaseHTTPMiddleware):
    """Log every route hit that carries an agent API key."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Quick check: skip uninteresting routes
        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        # Check for API key header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not api_key:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # Fire-and-forget: resolve agent and write log
        try:
            pool = get_pool()
            key_hash = hash_api_key(api_key)
            row = await pool.fetchrow("SELECT agent_id FROM agents WHERE api_key_hash = $1", key_hash)
            if row:
                agent_id = row["agent_id"]

                # Grab a snippet of the request body for POST/PUT (already consumed, use state if available)
                body_snippet: str | None = None
                if request.method in ("POST", "PUT", "PATCH"):
                    try:
                        # Body has been consumed by call_next; we can't re-read it.
                        # Store the path query params instead as a hint.
                        params = str(dict(request.query_params)) if request.query_params else None
                        body_snippet = params
                    except Exception:
                        pass

                ip = request.client.host if request.client else None

                await pool.execute(
                    """INSERT INTO agent_logs
                       (log_id, agent_id, method, path, status_code, duration_ms, ip_address, body_snippet, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())""",
                    str(uuid.uuid4()),
                    agent_id,
                    request.method,
                    path,
                    response.status_code,
                    duration_ms,
                    ip,
                    body_snippet,
                )
        except Exception:
            pass  # Never let logging break the actual request

        return response
