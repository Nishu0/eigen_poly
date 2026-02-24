import { db } from "../storage";
import type { TradeIntent } from "../types";
import { fetchMarketSnapshot } from "./market";
import { resolveRiskConfig, runRiskChecks } from "./risk";

function getTodayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export async function executeTradeIntent(intent: TradeIntent & { agentId: string }) {
  const account = db.accounts.get(intent.agentId);
  if (!account) {
    return { ok: false as const, status: 404, error: "Agent not registered" };
  }

  const market = await fetchMarketSnapshot(intent.marketId);
  const riskConfig = resolveRiskConfig(intent.riskConfig);

  const today = getTodayIsoDate();
  const tradedTodayUsd = db.trades
    .filter((t) => t.agentId === intent.agentId && t.createdAt.startsWith(today))
    .reduce((sum, t) => sum + t.amountUsd, 0);

  const risk = runRiskChecks({
    amountUsd: intent.amountUsd,
    market,
    riskConfig,
    tradedTodayUsd
  });

  if (!risk.ok) {
    return { ok: false as const, status: 422, error: risk.reason, market, riskConfig };
  }

  const price = intent.side === "YES" ? market.yesPrice : market.noPrice;
  const expectedShares = intent.amountUsd / Math.max(price, 0.01);
  const feeUsd = Number((intent.amountUsd * 0.005).toFixed(2));

  const markMove = market.volatility * (intent.confidence - 0.5) * 0.5;
  const grossPnl = (markMove * intent.amountUsd) / Math.max(price, 0.01);
  const pnlUsd = Number((grossPnl - feeUsd).toFixed(2));

  const current = db.balances.get(intent.agentId) ?? { polygonUsd: 0, solanaUsd: 0 };
  const nextPolygon = Number((current.polygonUsd - intent.amountUsd + pnlUsd).toFixed(2));
  db.balances.set(intent.agentId, { ...current, polygonUsd: nextPolygon });

  const createdAt = new Date().toISOString();
  db.trades.push({
    ...intent,
    createdAt,
    pnlUsd
  });

  return {
    ok: true as const,
    receipt: {
      agentId: intent.agentId,
      marketId: intent.marketId,
      side: intent.side,
      amountUsd: intent.amountUsd,
      expectedShares: Number(expectedShares.toFixed(4)),
      referencePrice: price,
      feeUsd,
      pnlUsd,
      chain: "polygon-safe",
      venue: market.source,
      executionAdapter: "live-market-exec-pipeline",
      executionReference: null,
      createdAt
    },
    market,
    riskConfig,
    account
  };
}
