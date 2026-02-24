from __future__ import annotations

from data_models import ArbitragePlan
from market_clients import fetch_all_markets, fetch_gnosis_markets, fetch_polymarket_markets
from strategies.arbitrage import build_arbitrage_plans

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:
    raise RuntimeError("Install MCP deps first: pip install -r requirements.txt") from exc

mcp = FastMCP("eigenpoly-strategy-mcp")


@mcp.tool()
def polymarket_markets(limit: int = 50) -> list[dict]:
    return [m.model_dump() for m in fetch_polymarket_markets(limit=limit)]


@mcp.tool()
def gnosis_markets(limit: int = 50) -> list[dict]:
    return [m.model_dump() for m in fetch_gnosis_markets(limit=limit)]


@mcp.tool()
def unified_markets(limit: int = 50) -> list[dict]:
    return [m.model_dump() for m in fetch_all_markets(limit=limit)]


@mcp.tool()
def arbitrage_plans(limit: int = 50, total_trade_amount: float = 10.0, min_profit: float = 0.005) -> list[dict]:
    plans: list[ArbitragePlan] = build_arbitrage_plans(
        limit=limit,
        total_trade_amount=total_trade_amount,
        min_profit=min_profit,
    )
    return [p.model_dump() for p in plans]


if __name__ == "__main__":
    mcp.run(transport="stdio")
