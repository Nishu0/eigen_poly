"""
Auto-freemonies engine — automatic smart money market trading via MetEngine x402.

Flow per cycle:
  1. Check agent's Solana USDC balance (MetEngine calls cost x402 micropayments)
  2. Call MetEngine /markets/opportunities for high-conviction market signals
  3. Filter out markets already held as open positions
  4. Pick top N markets (configurable via freemonies_max_markets, default 2)
  5. Execute a trade of freemonies_amount_per_market USDC per market
  6. Record trades + positions in DB

All config is per-agent in the DB:
  freemonies_max_markets        — markets to invest in per cycle (default 2)
  freemonies_amount_per_market  — USDC per trade (default $2.00, min $2.00)

Global env vars:
  FREEMONIES_INTERVAL_HOURS     — cron interval (default: same as rebalance = 3)
  METENGINE_BASE                — MetEngine base URL
  SOLANA_RPC_URL                — Solana RPC (default: mainnet-beta)
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from lib.agent_store import Agent, AgentStore
from lib.database import get_pool
from lib.position_storage import PositionEntry, PositionStorage, TradeStorage
from lib.tee_wallet import derive_solana_wallet, derive_wallet, is_tee_mode
from lib.wallet_manager import WalletManager
from scripts.trade import TradeExecutor

log = logging.getLogger("freemonies")

METENGINE_BASE = os.environ.get("METENGINE_BASE", "https://agent.metengine.xyz")
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


# ── Solana helpers ─────────────────────────────────────────────────────────────


async def _solana_usdc_balance(address: str) -> float:
    """Return USDC balance for a Solana address."""
    rpc = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.post(rpc, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [address, {"mint": SOLANA_USDC_MINT}, {"encoding": "jsonParsed"}],
            })
            accounts = resp.json().get("result", {}).get("value", [])
            if accounts:
                return float(
                    accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
                )
    except Exception as e:
        log.warning(f"Solana balance check failed for {address}: {e}")
    return 0.0


# ── x402 MetEngine fetch ───────────────────────────────────────────────────────


async def _pay_x402(privkey_b58: str, payment_info: dict) -> str:
    """Build x402 payment header for MetEngine."""
    try:
        from solders.keypair import Keypair
        import base58 as _b58
    except ImportError:
        raise RuntimeError("Install solders + base58: pip install solders base58")

    key_bytes = _b58.b58decode(privkey_b58)
    sender = Keypair.from_bytes(key_bytes)

    accepts = payment_info.get("accepts", [{}])[0]
    amount = accepts.get("maxAmountRequired", accepts.get("amount", "1000"))
    recipient = accepts.get("payTo", "")
    scheme = accepts.get("scheme", "exact")
    network = accepts.get("network", "solana-mainnet")

    nonce = int(time.time() * 1000)
    payload = {
        "x402Version": 1,
        "scheme": scheme,
        "network": network,
        "payload": {
            "signature": "",
            "authorization": {
                "from": str(sender.pubkey()),
                "to": recipient,
                "value": str(amount),
                "validAfter": str(nonce - 1000),
                "validBefore": str(nonce + 300_000),
                "nonce": str(nonce),
            },
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


async def _metengine_fetch(path: str, privkey_b58: str, params: Optional[dict] = None) -> dict:
    """Call MetEngine, handling x402 payment automatically."""
    url = f"{METENGINE_BASE}{path}"
    clean = {k: v for k, v in (params or {}).items() if v is not None}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=clean)
        if resp.status_code == 402:
            payment_header = await _pay_x402(privkey_b58, resp.json())
            resp = await client.get(
                url, params=clean,
                headers={"X-PAYMENT": payment_header, "Access-Control-Expose-Headers": "X-PAYMENT-RESPONSE"},
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"MetEngine {path} → {resp.status_code}: {resp.text[:200]}")
        return resp.json()


# ── DB helpers ─────────────────────────────────────────────────────────────────


async def _open_market_ids(agent_id: str) -> set[str]:
    """Return set of market_ids that already have open positions for this agent."""
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT market_id FROM positions WHERE agent_id=$1 AND status='open'",
        agent_id,
    )
    return {r["market_id"] for r in rows}


async def _record_freemonies_trade(
    agent_id: str,
    trade_id: str,
    market_id: str,
    question: str,
    side: str,
    amount_usd: float,
    entry_price: float,
    split_tx: Optional[str],
    clob_order_id: Optional[str],
    clob_filled: bool,
    status: str,
    error: Optional[str],
    position_id: Optional[str],
) -> None:
    ts = TradeStorage()
    ps = PositionStorage()

    await ts.record(
        trade_id=trade_id,
        agent_id=agent_id,
        market_id=market_id,
        question=question,
        side=side,
        amount_usd=amount_usd,
        entry_price=entry_price,
        split_tx=split_tx,
        clob_order_id=clob_order_id,
        clob_filled=clob_filled,
        status=status,
        error=error,
    )

    if status == "executed" and position_id:
        await ps.add(PositionEntry(
            position_id=position_id,
            agent_id=agent_id,
            market_id=market_id,
            question=question,
            position=side,
            token_id=None,
            entry_time=datetime.now(timezone.utc).isoformat(),
            entry_amount=amount_usd,
            entry_price=entry_price,
            split_tx=split_tx,
            clob_order_id=clob_order_id,
            clob_filled=clob_filled,
        ))


# ── Market parsing ─────────────────────────────────────────────────────────────


def _parse_opportunities(data: dict) -> list[dict]:
    """Extract market list from MetEngine opportunities response.

    Handles multiple response shapes defensively.
    Returns list of dicts with at least: market_id, side.
    """
    # Try common top-level keys
    for key in ("opportunities", "markets", "data", "results"):
        items = data.get(key)
        if isinstance(items, list) and items:
            return items

    # If response is already a list
    if isinstance(data, list):
        return data

    return []


def _market_id_from_item(item: dict) -> Optional[str]:
    for key in ("market_id", "marketId", "condition_id", "conditionId", "id"):
        val = item.get(key)
        if val:
            return str(val)
    return None


def _side_from_item(item: dict) -> str:
    for key in ("recommended_side", "recommendedSide", "side", "signal_side"):
        val = item.get(key, "")
        if isinstance(val, str) and val.upper() in ("YES", "NO"):
            return val.upper()
    return "YES"  # default to YES when signal is bullish but side not specified


# ── Core engine ────────────────────────────────────────────────────────────────


async def run_freemonies_for_agent(agent: Agent) -> dict:
    """Run one freemonies cycle for a single agent. Returns result dict."""
    result: dict = {
        "agent_id": agent.agent_id,
        "action": "skip",
        "reason": "",
        "trades": [],
        "error": None,
    }

    max_markets = agent.freemonies_max_markets or 2
    amount_per_market = max(agent.freemonies_amount_per_market or 2.0, 2.0)

    # 1. Get Solana key for x402 payments
    sol_key_b58: Optional[str] = None
    sol_address: Optional[str] = None

    if is_tee_mode():
        try:
            sol_wallet = derive_solana_wallet(agent.wallet_index)
            sol_key_b58 = sol_wallet.private_key_b58
            sol_address = sol_wallet.address
        except Exception as e:
            result["error"] = f"Solana key unavailable: {e}"
            return result
    else:
        sol_key_b58 = os.environ.get("METENGINE_SOLANA_KEY")
        sol_address = agent.solana_wallet or ""

    if not sol_key_b58:
        result["reason"] = "no Solana key available (set MNEMONIC or METENGINE_SOLANA_KEY)"
        return result

    # 2. Check Solana USDC balance — needed to pay for MetEngine x402 calls
    if sol_address:
        sol_usdc = await _solana_usdc_balance(sol_address)
        result["solana_usdc"] = sol_usdc
        if sol_usdc <= 0:
            result["reason"] = f"Solana USDC balance is 0 — fund {sol_address} to enable MetEngine calls"
            return result
    else:
        result["reason"] = "no Solana address on record"
        return result

    # 3. Fetch high-conviction opportunities from MetEngine
    try:
        data = await _metengine_fetch(
            "/markets/opportunities",
            sol_key_b58,
            params={"min_signal_strength": "HIGH"},
        )
    except Exception as e:
        # Fallback to high-conviction endpoint
        try:
            data = await _metengine_fetch(
                "/markets/high-conviction",
                sol_key_b58,
                params={"min_smart_wallets": 5, "min_avg_score": 65},
            )
        except Exception as e2:
            result["error"] = f"MetEngine fetch failed: {e} / fallback: {e2}"
            return result

    opportunities = _parse_opportunities(data)
    if not opportunities:
        result["reason"] = "MetEngine returned no opportunities"
        return result

    result["opportunities_found"] = len(opportunities)

    # 4. Filter out markets already held
    held = await _open_market_ids(agent.agent_id)
    fresh = [o for o in opportunities if _market_id_from_item(o) not in held]

    if not fresh:
        result["reason"] = "all opportunities already held as open positions"
        return result

    # Pick top N
    targets = fresh[:max_markets]

    # 5. Get EVM wallet for Polygon trades
    wallet = WalletManager.from_tee(agent.wallet_index)
    if not wallet.is_unlocked:
        result["error"] = "EVM wallet unavailable"
        return result

    # 6. Execute trades via the Safe
    executor = TradeExecutor(wallet, safe_address=agent.polygon_safe or None)
    traded = 0

    for item in targets:
        market_id = _market_id_from_item(item)
        if not market_id:
            continue

        side = _side_from_item(item)
        trade_id = f"fm_{uuid.uuid4().hex[:16]}"
        trade_result = {
            "market_id": market_id,
            "side": side,
            "amount_usd": amount_per_market,
            "status": "failed",
            "error": None,
            "trade_id": trade_id,
        }

        try:
            exec_result = await executor.buy_position(
                market_id=market_id,
                position=side,
                amount=amount_per_market,
                skip_clob_sell=False,
            )

            position_id = str(uuid.uuid4()) if exec_result.success else None
            status = "executed" if exec_result.success else "failed"

            await _record_freemonies_trade(
                agent_id=agent.agent_id,
                trade_id=trade_id,
                market_id=market_id,
                question=exec_result.question or market_id,
                side=side,
                amount_usd=amount_per_market,
                entry_price=exec_result.entry_price or 0.0,
                split_tx=exec_result.split_tx,
                clob_order_id=exec_result.clob_order_id,
                clob_filled=exec_result.clob_filled,
                status=status,
                error=exec_result.error,
                position_id=position_id,
            )

            trade_result["status"] = status
            trade_result["entry_price"] = exec_result.entry_price
            trade_result["split_tx"] = exec_result.split_tx
            trade_result["position_id"] = position_id
            if exec_result.success:
                traded += 1

        except Exception as e:
            trade_result["error"] = str(e)
            log.error(f"[{agent.agent_id}] freemonies trade failed for {market_id}: {e}")

        result["trades"].append(trade_result)

    wallet.lock()

    result["action"] = "traded" if traded > 0 else "skip"
    result["markets_traded"] = traded
    result["reason"] = f"invested ${amount_per_market} in {traded}/{len(targets)} markets"

    log.info(
        f"[freemonies] {agent.agent_id}: {traded} trades executed"
        f" @ ${amount_per_market} each (sol_usdc={sol_usdc:.4f})"
    )
    return result


async def run_freemonies_cron() -> None:
    """Run freemonies for all agents with auto_freemonies=True."""
    store = AgentStore()
    try:
        agents = await store.list_agents()
    except Exception as e:
        log.error(f"[cron] failed to list agents: {e}")
        return

    eligible = [a for a in agents if a.auto_freemonies]
    log.info(f"[freemonies cron] {len(eligible)}/{len(agents)} agents eligible")

    for agent in eligible:
        try:
            result = await run_freemonies_for_agent(agent)
            log.info(
                f"[freemonies cron] {agent.agent_id}: {result.get('action')}"
                f" — {result.get('reason', '')}"
            )
        except Exception as e:
            log.error(f"[freemonies cron] {agent.agent_id} unhandled error: {e}")


async def start_freemonies_cron() -> None:
    """Background cron. Starts 90s after boot (offset from rebalance cron), then every N hours."""
    interval_secs = int(os.environ.get("FREEMONIES_INTERVAL_HOURS",
                                        os.environ.get("REBALANCE_INTERVAL_HOURS", "3"))) * 3600
    await asyncio.sleep(90)  # offset from rebalance cron (starts at 60s)
    log.info(f"[freemonies cron] started — interval: {interval_secs // 3600}h")
    while True:
        try:
            await run_freemonies_cron()
        except Exception as e:
            log.error(f"[freemonies cron] top-level error: {e}")
        await asyncio.sleep(interval_secs)
