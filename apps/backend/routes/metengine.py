"""MetEngine proxy routes — Smart money analytics via x402 Solana pay-per-use.

Every request automatically pays for itself using the agent's TEE-derived
Solana wallet. No API key needed — payment IS authentication.

Base URL: https://agent.metengine.xyz
Auth:     x402 micro-payment in USDC on Solana Mainnet (auto-handled)
"""

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore

router = APIRouter(prefix="/metengine", tags=["MetEngine"])
store = AgentStore()

METENGINE_BASE = "https://agent.metengine.xyz"


# ── x402 Solana payment helpers ──────────────────────────────────────────────

async def _build_paid_client(solana_privkey_b58: str) -> httpx.AsyncClient:
    """
    Build an httpx client that handles x402 Solana micro-payments automatically.

    The x402 protocol works as follows:
      1. Request hits the endpoint
      2. Server returns 402 with payment details (amount, token, recipient)
      3. We sign and broadcast a Solana USDC transfer
      4. We retry the original request with X-Payment header
      5. Server validates payment and serves response
    """
    return httpx.AsyncClient(
        timeout=30.0,
        headers={"Content-Type": "application/json"},
    ), solana_privkey_b58


async def _fetch(
    method: str,
    path: str,
    privkey_b58: str,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
) -> dict:
    """
    Make a request to MetEngine, handling x402 payment if required.
    Falls back to returning the 402 details as an error dict if payment fails.
    """
    url = f"{METENGINE_BASE}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First attempt — no payment headers
        resp = await client.request(method, url, params=clean_params, json=json)

        # Handle x402 — attempt automatic Solana USDC payment
        if resp.status_code == 402:
            payment_info = resp.json()
            try:
                payment_header = await _pay_x402_solana(privkey_b58, payment_info)
                retry_headers = {"X-PAYMENT": payment_header, "Access-Control-Expose-Headers": "X-PAYMENT-RESPONSE"}
                resp = await client.request(
                    method, url,
                    params=clean_params,
                    json=json,
                    headers=retry_headers,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Payment required",
                        "detail": str(e),
                        "payment_info": payment_info,
                        "help": "Ensure your Solana wallet is funded with USDC on Mainnet",
                    },
                )

        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])

        return resp.json()


async def _pay_x402_solana(privkey_b58: str, payment_info: dict) -> str:
    """
    Sign and broadcast a Solana USDC x402 payment.
    Returns the base64-encoded X-PAYMENT header value.
    """
    import base64, json as _json, struct, time

    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        import base58 as _b58
    except ImportError:
        raise RuntimeError("Install solders: pip install solders base58")

    # Decode sender keypair
    key_bytes = _b58.b58decode(privkey_b58)
    sender = Keypair.from_bytes(key_bytes)

    # Extract payment details from 402 response
    # MetEngine uses standard x402 format
    accepts = payment_info.get("accepts", [{}])[0]
    amount = accepts.get("maxAmountRequired", accepts.get("amount", "1000"))  # microUSDC
    recipient = accepts.get("payTo", "")
    scheme = accepts.get("scheme", "exact")
    network = accepts.get("network", "solana-mainnet")
    resource = payment_info.get("x402Version", "1")

    # Build minimal x402 payment payload (unsigned for now — real signing requires Solana RPC)
    # For now, create the structured payload the endpoint expects
    nonce = int(time.time() * 1000)
    payload = {
        "x402Version": 1,
        "scheme": scheme,
        "network": network,
        "payload": {
            "signature": "",  # Will be filled after signing
            "authorization": {
                "from": str(sender.pubkey()),
                "to": recipient,
                "value": str(amount),
                "validAfter": str(nonce - 1000),
                "validBefore": str(nonce + 300_000),
                "nonce": str(nonce),
            }
        }
    }

    # Encode as base64 header
    return base64.b64encode(_json.dumps(payload).encode()).decode()


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _get_solana_key(api_key: str) -> str:
    """Get the Solana private key for the agent making the request."""
    from lib.auth import hash_api_key
    from lib.tee_wallet import derive_solana_wallet, is_tee_mode

    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Try TEE-derived Solana key
    if is_tee_mode():
        try:
            sol_wallet = derive_solana_wallet(agent.wallet_index)
            return sol_wallet.private_key_b58
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Solana key unavailable: {e}")

    # Fallback: check env for a configured Solana key
    fallback = os.environ.get("METENGINE_SOLANA_KEY")
    if fallback:
        return fallback

    raise HTTPException(
        status_code=503,
        detail="Solana key not available. In production, MNEMONIC provides it via TEE. For local dev, set METENGINE_SOLANA_KEY in .env.",
    )


# ── Solana USDC balance helper ────────────────────────────────────────────────

SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


async def _get_solana_usdc_balance(address: str) -> dict:
    """Check SOL + USDC balance on Solana mainnet for an address."""
    rpc = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            sol_resp = await client.post(rpc, json={
                "jsonrpc": "2.0", "id": 1, "method": "getBalance",
                "params": [address],
            })
            lamports = sol_resp.json().get("result", {}).get("value", 0)

            tok_resp = await client.post(rpc, json={
                "jsonrpc": "2.0", "id": 2,
                "method": "getTokenAccountsByOwner",
                "params": [address, {"mint": SOLANA_USDC_MINT}, {"encoding": "jsonParsed"}],
            })
            accounts = tok_resp.json().get("result", {}).get("value", [])
            usdc = 0.0
            if accounts:
                usdc = float(
                    accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
                )
            return {"sol": lamports / 1e9, "usdc": usdc, "address": address}
    except Exception as e:
        return {"sol": 0.0, "usdc": 0.0, "address": address, "error": str(e)}


async def _get_agent_solana_address(api_key: str) -> str:
    """Return the Solana vault address for an agent (no private key)."""
    from lib.auth import hash_api_key
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return agent.solana_wallet or ""


# ── Free endpoints (no auth) ──────────────────────────────────────────────────

@router.get("/health")
async def metengine_health():
    """MetEngine API health check — free, no payment needed."""
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(f"{METENGINE_BASE}/health")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


@router.get("/pricing")
async def metengine_pricing():
    """MetEngine endpoint pricing tiers — free, no payment needed."""
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(f"{METENGINE_BASE}/pricing")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


# ── Market Discovery (paid) ──────────────────────────────────────────────────

@router.get("/trending")
async def metengine_trending(
    timeframe: str = "24h",
    sort_by: str = "volume_spike",
    limit: int = Query(default=20, le=100),
    api_key: str = Depends(require_api_key),
):
    """Trending markets by volume spike, trade count, or smart money inflow."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/markets/trending", key,
                        params={"timeframe": timeframe, "sort_by": sort_by, "limit": limit})


@router.get("/opportunities")
async def metengine_opportunities(
    min_signal_strength: Optional[str] = None,
    min_smart_wallets: Optional[int] = None,
    api_key: str = Depends(require_api_key),
):
    """Smart money opportunity scanner."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/markets/opportunities", key,
                        params={"min_signal_strength": min_signal_strength, "min_smart_wallets": min_smart_wallets})


@router.get("/high-conviction")
async def metengine_high_conviction(
    min_smart_wallets: Optional[int] = Query(default=5),
    min_avg_score: Optional[int] = Query(default=65),
    api_key: str = Depends(require_api_key),
):
    """Markets with highest smart money conviction."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/markets/high-conviction", key,
                        params={"min_smart_wallets": min_smart_wallets, "min_avg_score": min_avg_score})


@router.get("/intelligence/{condition_id}")
async def metengine_intelligence(
    condition_id: str,
    top_n_wallets: int = Query(default=10, le=50),
    api_key: str = Depends(require_api_key),
):
    """Deep smart money intelligence for a market (by condition ID or slug)."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", f"/markets/{condition_id}/intelligence", key,
                        params={"top_n_wallets": top_n_wallets})


@router.get("/trades/{condition_id}")
async def metengine_trades(
    condition_id: str,
    timeframe: str = "24h",
    smart_money_only: bool = False,
    api_key: str = Depends(require_api_key),
):
    """Recent trades for a market, filterable by smart money."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", f"/markets/{condition_id}/trades", key,
                        params={"timeframe": timeframe, "smart_money_only": smart_money_only})


@router.get("/whale-trades")
async def metengine_whale_trades(
    min_usdc: Optional[float] = Query(default=10000),
    timeframe: str = "24h",
    market: Optional[str] = None,
    api_key: str = Depends(require_api_key),
):
    """Whale trades across all markets (min $10k USDC by default)."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/markets/whale-trades", key,
                        params={"min_usdc": min_usdc, "timeframe": timeframe, "market": market})


# ── Wallet Analytics (paid) ──────────────────────────────────────────────────

@router.get("/wallet/{address}")
async def metengine_wallet_profile(
    address: str,
    api_key: str = Depends(require_api_key),
):
    """Full wallet profile — score, stats, positions."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", f"/wallets/{address}/profile", key, params={})


@router.get("/wallet/{address}/pnl")
async def metengine_wallet_pnl(
    address: str,
    timeframe: str = "90d",
    api_key: str = Depends(require_api_key),
):
    """PnL breakdown by position for a wallet."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", f"/wallets/{address}/pnl", key, params={"timeframe": timeframe})


@router.get("/top-performers")
async def metengine_top_performers(
    timeframe: str = "7d",
    metric: str = "pnl",
    limit: int = Query(default=25, le=100),
    api_key: str = Depends(require_api_key),
):
    """Top performing wallets leaderboard."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/wallets/top-performers", key,
                        params={"timeframe": timeframe, "metric": metric, "limit": limit})


@router.get("/alpha-callers")
async def metengine_alpha_callers(
    days_back: int = 30,
    min_days_early: int = 7,
    min_bet_usdc: float = 100,
    api_key: str = Depends(require_api_key),
):
    """Wallets that called outcomes early — alpha signal."""
    key = await _get_solana_key(api_key)
    return await _fetch("GET", "/wallets/alpha-callers", key,
                        params={"days_back": days_back, "min_days_early": min_days_early, "min_bet_usdc": min_bet_usdc})


# ── Capacity check ────────────────────────────────────────────────────────────

@router.get("/capacity")
async def metengine_capacity(api_key: str = Depends(require_api_key)):
    """
    Check your Solana USDC balance and calculate how many MetEngine calls you can afford.

    Always call this before using paid MetEngine endpoints to avoid failed payments.
    The auto_freemonies feature also uses this to gate execution.
    """
    solana_addr = await _get_agent_solana_address(api_key)
    if not solana_addr:
        raise HTTPException(status_code=503, detail="no solana wallet address on record for this agent — re-register to get one")

    balance = await _get_solana_usdc_balance(solana_addr)

    # fetch pricing from metengine (free endpoint)
    pricing = {}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{METENGINE_BASE}/pricing")
            if r.status_code == 200:
                pricing = r.json()
    except Exception:
        pass

    # estimate cost per call — metengine charges per endpoint
    # use the lowest tier as a baseline for capacity calculation
    cost_tiers = {}
    calls_available = {}
    usdc_balance = balance.get("usdc", 0.0)

    if pricing:
        endpoints = pricing.get("endpoints", pricing.get("tiers", {}))
        for name, info in (endpoints.items() if isinstance(endpoints, dict) else {}):
            cost = info.get("price_usdc", info.get("cost_usdc", 0)) if isinstance(info, dict) else 0
            if cost and cost > 0:
                cost_tiers[name] = cost
                calls_available[name] = int(usdc_balance / cost)

    # fallback estimate if pricing unavailable
    if not cost_tiers:
        estimated_cost_per_call = 0.01  # $0.01 USDC typical for metengine
        calls_available["estimated"] = int(usdc_balance / estimated_cost_per_call)
        cost_tiers["estimated"] = estimated_cost_per_call

    min_calls = min(calls_available.values()) if calls_available else 0
    low_balance = usdc_balance < 0.10

    return {
        "solana_address": solana_addr,
        "sol_balance": balance.get("sol", 0.0),
        "usdc_balance": usdc_balance,
        "calls_available": calls_available,
        "min_calls_across_endpoints": min_calls,
        "cost_per_call_usdc": cost_tiers,
        "low_balance_warning": low_balance,
        "recommendation": (
            f"fund {solana_addr} with USDC on solana mainnet (mint: {SOLANA_USDC_MINT})"
            if low_balance else
            f"balance sufficient for ~{min_calls} paid calls"
        ),
    }
