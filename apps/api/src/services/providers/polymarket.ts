export type ExternalMarket = {
  id: string;
  question: string;
  yesPrice: number;
  noPrice: number;
  liquidityUsd: number;
  source: "polymarket";
};

type PolymarketGammaMarket = {
  id?: string;
  conditionId?: string;
  question?: string;
  outcomes?: string;
  outcomePrices?: string;
  liquidityNum?: number;
};

function parseOutcomePrices(raw?: string): [number, number] | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as number[];
    if (!Array.isArray(parsed) || parsed.length < 2) return null;
    const yes = Number(parsed[0]);
    const no = Number(parsed[1]);
    if (Number.isNaN(yes) || Number.isNaN(no)) return null;
    return [yes, no];
  } catch {
    return null;
  }
}

export async function fetchPolymarketMarkets(limit = 50): Promise<ExternalMarket[]> {
  const baseUrl = process.env.POLYMARKET_GAMMA_BASE_URL ?? "https://gamma-api.polymarket.com";
  const url = `${baseUrl}/markets?active=true&closed=false&limit=${limit}`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Polymarket request failed with status ${res.status}`);
  }

  const data = (await res.json()) as PolymarketGammaMarket[];
  return data
    .map((m) => {
      const prices = parseOutcomePrices(m.outcomePrices);
      if (!prices) return null;
      const [yes, no] = prices;
      return {
        id: m.conditionId ?? m.id ?? "",
        question: m.question ?? "",
        yesPrice: yes,
        noPrice: no,
        liquidityUsd: Number(m.liquidityNum ?? 0),
        source: "polymarket" as const
      };
    })
    .filter((m): m is ExternalMarket => Boolean(m?.id && m.question));
}
