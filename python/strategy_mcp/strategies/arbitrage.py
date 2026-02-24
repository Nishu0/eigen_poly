from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cachetools import TTLCache

from data_models import ArbitragePlan, CorrelatedMarketPair, Correlation, MarketTrade
from market_clients import fetch_all_markets

RECENTLY_TRADED_MARKET_IDS: TTLCache[str, bool] = TTLCache(maxsize=10000, ttl=3 * 60 * 60)


def was_market_recently_traded(market_id: str) -> bool:
    return market_id.lower() in RECENTLY_TRADED_MARKET_IDS


def mark_markets_traded(primary_market_id: str, related_market_id: str) -> None:
    RECENTLY_TRADED_MARKET_IDS[primary_market_id.lower()] = True
    RECENTLY_TRADED_MARKET_IDS[related_market_id.lower()] = True


def _simple_correlation(main_q: str, related_q: str) -> Correlation:
    # Placeholder deterministic heuristic; replace with LLM correlation chain.
    main_tokens = {t for t in main_q.lower().split() if len(t) > 3}
    related_tokens = {t for t in related_q.lower().split() if len(t) > 3}

    overlap = len(main_tokens.intersection(related_tokens))
    if overlap >= 5:
        return Correlation(near_perfect_correlation=True, reasoning="High token overlap between market questions.")
    if overlap <= 1:
        return Correlation(near_perfect_correlation=None, reasoning="Weak semantic overlap.")
    return Correlation(near_perfect_correlation=False, reasoning="Moderate overlap, possibly inverse or weakly related.")


def build_arbitrage_plans(limit: int = 50, total_trade_amount: float = 10.0, min_profit: float = 0.005) -> list[ArbitragePlan]:
    markets = fetch_all_markets(limit=limit)

    plans: list[ArbitragePlan] = []
    for i, main in enumerate(markets):
        for related in markets[i + 1 : i + 8]:
            pair = CorrelatedMarketPair(
                main_market=main,
                related_market=related,
                correlation=_simple_correlation(main.question, related.question),
            )

            if pair.main_market_and_related_market_equal:
                continue
            if was_market_recently_traded(main.id) or was_market_recently_traded(related.id):
                continue

            potential = pair.potential_profit_per_bet_unit()
            if potential <= min_profit:
                continue

            split = pair.split_bet_amount_between_yes_and_no(total_trade_amount)
            trades = [
                MarketTrade(market=main, outcome=split.main_market_bet.direction, amount=split.main_market_bet.size),
                MarketTrade(market=related, outcome=split.related_market_bet.direction, amount=split.related_market_bet.size),
            ]

            plans.append(
                ArbitragePlan(pair=pair, potential_profit_per_unit=potential, trades=trades)
            )
            mark_markets_traded(main.id, related.id)

            if len(plans) >= 20:
                return plans

    return plans
