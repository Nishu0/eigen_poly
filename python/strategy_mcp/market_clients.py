from __future__ import annotations

import os
from typing import Any

import requests

from data_models import AgentMarket


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def fetch_polymarket_markets(limit: int = 50) -> list[AgentMarket]:
    base_url = os.getenv("POLYMARKET_GAMMA_BASE_URL", "https://gamma-api.polymarket.com")
    res = requests.get(f"{base_url}/markets", params={"active": "true", "closed": "false", "limit": limit}, timeout=20)
    res.raise_for_status()

    rows = res.json()
    out: list[AgentMarket] = []
    for row in rows:
        raw_prices = row.get("outcomePrices")
        if not raw_prices:
            continue
        try:
            prices = __import__("json").loads(raw_prices)
            if len(prices) < 2:
                continue
        except Exception:
            continue

        market_id = row.get("conditionId") or row.get("id")
        question = row.get("question") or ""
        if not market_id or not question:
            continue

        yes_price = _safe_float(prices[0], 0.5)
        no_price = _safe_float(prices[1], 0.5)

        out.append(
            AgentMarket(
                id=str(market_id),
                question=question,
                p_yes=yes_price,
                p_no=no_price,
                source="polymarket",
            )
        )
    return out


def fetch_gnosis_markets(limit: int = 50) -> list[AgentMarket]:
    endpoint = os.getenv("GNOSIS_OMEN_SUBGRAPH_URL", "https://api.thegraph.com/subgraphs/name/protofire/omen-xdai")

    query = """
    query OmenMarkets($first: Int!) {
      fixedProductMarketMakers(
        first: $first
        where: {isPendingArbitration: false}
        orderBy: creationTimestamp
        orderDirection: desc
      ) {
        id
        title
        outcomeTokenMarginalPrices
      }
    }
    """

    res = requests.post(endpoint, json={"query": query, "variables": {"first": limit}}, timeout=20)
    res.raise_for_status()
    data = res.json().get("data", {}).get("fixedProductMarketMakers", [])

    out: list[AgentMarket] = []
    for row in data:
        prices = row.get("outcomeTokenMarginalPrices") or []
        if len(prices) < 2:
            continue

        out.append(
            AgentMarket(
                id=str(row.get("id")),
                question=row.get("title") or "",
                p_yes=_safe_float(prices[0], 0.5),
                p_no=_safe_float(prices[1], 0.5),
                source="gnosis",
            )
        )
    return [m for m in out if m.id and m.question]


def fetch_all_markets(limit: int = 50) -> list[AgentMarket]:
    markets: list[AgentMarket] = []
    markets.extend(fetch_polymarket_markets(limit=limit))
    markets.extend(fetch_gnosis_markets(limit=limit))
    return markets
