"""Google OAuth routes — login, callback, session management.

Uses Google OAuth 2.0 for human login. Sessions stored as signed JWT cookies.

Env vars:
  GOOGLE_CLIENT_ID      — Google OAuth client ID
  GOOGLE_CLIENT_SECRET  — Google OAuth client secret
  JWT_SECRET            — Secret for signing session cookies
  FRONTEND_URL          — Frontend URL for redirects
"""

import os
import uuid
import time
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from lib.database import get_pool


router = APIRouter(prefix="/oauth", tags=["OAuth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "eigenpoly-dev-secret-change-me")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

COOKIE_NAME = "eigenpoly_session"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days


def _get_redirect_uri() -> str:
    """Get the OAuth redirect URI."""
    backend = BACKEND_URL or f"{FRONTEND_URL}"
    return f"{backend}/oauth/google/callback"


def _create_session_token(user_id: str, email: str, name: str) -> str:
    """Create a signed JWT session token."""
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": int(time.time()),
        "exp": int(time.time()) + COOKIE_MAX_AGE,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_session_token(token: str) -> dict | None:
    """Decode and verify a session token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user(request: Request) -> dict | None:
    """Extract current user from session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return _decode_session_token(token)


@router.get("/google")
async def google_login(request: Request, redirect: str = ""):
    """Redirect to Google OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    # Store intended redirect in a state param
    state = redirect or "/dashboard"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "/dashboard"):
    """Handle Google OAuth callback — create/find user, set session cookie."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": _get_redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Google token exchange failed")
        tokens = token_resp.json()

        # Get user info
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")
        userinfo = userinfo_resp.json()

    google_sub = userinfo.get("sub", "")
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    avatar = userinfo.get("picture", "")

    # Create or find user
    pool = get_pool()
    user = await pool.fetchrow("SELECT * FROM users WHERE google_sub = $1", google_sub)

    if user:
        user_id = user["user_id"]
        # Update name/avatar if changed
        await pool.execute(
            "UPDATE users SET name = $1, avatar_url = $2 WHERE user_id = $3",
            name, avatar, user_id,
        )
    else:
        user_id = str(uuid.uuid4())
        await pool.execute(
            """INSERT INTO users (user_id, email, name, avatar_url, google_sub)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (email) DO UPDATE SET google_sub = $5, name = $3, avatar_url = $4""",
            user_id, email, name, avatar, google_sub,
        )

    # Create session token
    session_token = _create_session_token(user_id, email, name)

    # Redirect to frontend with session cookie
    redirect_url = f"{FRONTEND_URL}{state}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        session_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
    )
    return response


@router.get("/me")
async def get_me(request: Request):
    """Return current logged-in user from session cookie."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    pool = get_pool()
    db_user = await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user["sub"])
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "userId": db_user["user_id"],
        "email": db_user["email"],
        "name": db_user["name"],
        "avatarUrl": db_user["avatar_url"],
    }


@router.post("/logout")
async def logout():
    """Clear session cookie."""
    response = Response(content='{"ok": true}', media_type="application/json")
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
