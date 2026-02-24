from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


OutcomeStr = Literal["YES", "NO"]


class AgentMarket(BaseModel):
    id: str
    question: str
    p_yes: float
    p_no: float
    source: Literal["polymarket", "gnosis"]

    def get_outcome_str_from_bool(self, v: bool) -> OutcomeStr:
        return "YES" if v else "NO"


class Bet(BaseModel):
    direction: OutcomeStr
    size: float


class Correlation(BaseModel):
    near_perfect_correlation: Optional[bool]
    reasoning: str


class ArbitrageBet(BaseModel):
    main_market_bet: Bet
    related_market_bet: Bet


class CorrelatedMarketPair(BaseModel):
    main_market: AgentMarket
    related_market: AgentMarket
    correlation: Correlation

    @property
    def main_market_and_related_market_equal(self) -> bool:
        return self.main_market.id.lower() == self.related_market.id.lower()

    def potential_profit_per_bet_unit(self) -> float:
        if self.correlation.near_perfect_correlation is None:
            return 0.0

        bet_direction_main, bet_direction_related = self.bet_directions()
        p_main = self.main_market.p_yes if bet_direction_main else self.main_market.p_no
        p_related = self.related_market.p_yes if bet_direction_related else self.related_market.p_no

        denominator = p_main + p_related
        return (1 / denominator) - 1 if denominator > 0 else 0.0

    def bet_directions(self) -> tuple[bool, bool]:
        correlation = self.correlation.near_perfect_correlation
        if correlation is None:
            return (True, False)

        if correlation:
            yes_no = self.main_market.p_yes + self.related_market.p_no
            no_yes = self.main_market.p_no + self.related_market.p_yes
            return (True, False) if yes_no <= no_yes else (False, True)

        yes_yes = self.main_market.p_yes + self.related_market.p_yes
        no_no = self.main_market.p_no + self.related_market.p_no
        return (True, True) if yes_yes <= no_no else (False, False)

    def split_bet_amount_between_yes_and_no(self, total_bet_amount: float) -> ArbitrageBet:
        bet_direction_main, bet_direction_related = self.bet_directions()

        p_main = self.main_market.p_yes if bet_direction_main else self.main_market.p_no
        p_related = self.related_market.p_yes if bet_direction_related else self.related_market.p_no

        total_probability = max(p_main + p_related, 1e-8)
        bet_main = total_bet_amount * p_main / total_probability
        bet_related = total_bet_amount * p_related / total_probability

        return ArbitrageBet(
            main_market_bet=Bet(
                direction=self.main_market.get_outcome_str_from_bool(bet_direction_main),
                size=bet_main,
            ),
            related_market_bet=Bet(
                direction=self.related_market.get_outcome_str_from_bool(bet_direction_related),
                size=bet_related,
            ),
        )


class MarketTrade(BaseModel):
    market: AgentMarket
    outcome: OutcomeStr
    amount: float


class ArbitragePlan(BaseModel):
    pair: CorrelatedMarketPair
    potential_profit_per_unit: float
    trades: list[MarketTrade]
