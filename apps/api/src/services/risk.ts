import type { MarketSnapshot } from "./market";

export type RiskConfig = {
  maxPositionUsd: number;
  maxSpreadBps: number;
  maxDailyUsd: number;
};

export function resolveRiskConfig(raw?: Partial<RiskConfig>): RiskConfig {
  return {
    maxPositionUsd: raw?.maxPositionUsd ?? 250,
    maxSpreadBps: raw?.maxSpreadBps ?? 50,
    maxDailyUsd: raw?.maxDailyUsd ?? 1000
  };
}

export function runRiskChecks(input: {
  amountUsd: number;
  market: MarketSnapshot;
  riskConfig: RiskConfig;
  tradedTodayUsd: number;
}): { ok: true } | { ok: false; reason: string } {
  if (input.amountUsd > input.riskConfig.maxPositionUsd) {
    return { ok: false, reason: "amount exceeds maxPositionUsd" };
  }

  if (input.market.spreadBps > input.riskConfig.maxSpreadBps) {
    return { ok: false, reason: "market spread exceeds maxSpreadBps" };
  }

  if (input.tradedTodayUsd + input.amountUsd > input.riskConfig.maxDailyUsd) {
    return { ok: false, reason: "daily traded amount exceeds maxDailyUsd" };
  }

  return { ok: true };
}
