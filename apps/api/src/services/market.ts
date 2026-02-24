import { fetchGnosisMarkets } from "./providers/gnosis";
import { fetchPolymarketMarkets } from "./providers/polymarket";

export type MarketSnapshot = {
  marketId: string;
  question: string;
  yesPrice: number;
  noPrice: number;
  liquidityUsd: number;
  spreadBps: number;
  volatility: number;
  source: "polymarket" | "gnosis";
};

function calcSpreadBps(yes: number, no: number): number {
  const fair = Math.max(yes + no, 0.0001);
  return Math.round(Math.abs(1 - fair) * 10000);
}

function calcProxyVolatility(yes: number): number {
  const distance = Math.abs(yes - 0.5);
  return Number((0.4 - Math.min(distance, 0.4) * 0.75).toFixed(3));
}

export async function fetchMarketSnapshot(marketId: string): Promise<MarketSnapshot> {
  const [poly, gnosis] = await Promise.allSettled([fetchPolymarketMarkets(200), fetchGnosisMarkets(200)]);

  const polyMarkets = poly.status === "fulfilled" ? poly.value : [];
  const gnosisMarkets = gnosis.status === "fulfilled" ? gnosis.value : [];

  const found = [...polyMarkets, ...gnosisMarkets].find((m) => m.id.toLowerCase() === marketId.toLowerCase());

  if (!found) {
    const polyErr = poly.status === "rejected" ? poly.reason : null;
    const gnosisErr = gnosis.status === "rejected" ? gnosis.reason : null;
    throw new Error(
      `Market ${marketId} not found in live providers. polymarket_error=${polyErr ? String(polyErr) : "none"} gnosis_error=${gnosisErr ? String(gnosisErr) : "none"}`
    );
  }

  return {
    marketId: found.id,
    question: found.question,
    yesPrice: found.yesPrice,
    noPrice: found.noPrice,
    liquidityUsd: found.liquidityUsd,
    spreadBps: calcSpreadBps(found.yesPrice, found.noPrice),
    volatility: calcProxyVolatility(found.yesPrice),
    source: found.source
  };
}

export async function fetchUnifiedMarkets(limit = 50) {
  const [poly, gnosis] = await Promise.allSettled([fetchPolymarketMarkets(limit), fetchGnosisMarkets(limit)]);

  const polymarket = poly.status === "fulfilled" ? poly.value : [];
  const gnosisMarkets = gnosis.status === "fulfilled" ? gnosis.value : [];

  return {
    polymarket,
    gnosis: gnosisMarkets,
    errors: {
      polymarket: poly.status === "rejected" ? String(poly.reason) : null,
      gnosis: gnosis.status === "rejected" ? String(gnosis.reason) : null
    }
  };
}

export async function getMarketAnalysis() {
  const unified = await fetchUnifiedMarkets(25);
  return {
    tabs: ["Polymarket", "Gnosis", "Mispriced", "Cross-Venue"],
    engine: "Live Polymarket + Gnosis/Omen feeds",
    status: "live",
    counts: {
      polymarket: unified.polymarket.length,
      gnosis: unified.gnosis.length
    },
    errors: unified.errors
  };
}
