export type ExternalMarket = {
  id: string;
  question: string;
  yesPrice: number;
  noPrice: number;
  liquidityUsd: number;
  source: "gnosis";
};

type OmenResponse = {
  data?: {
    fixedProductMarketMakers?: Array<{
      id: string;
      title?: string;
      outcomes?: string[];
      outcomeTokenMarginalPrices?: string[];
      collateralVolumeUSD?: string;
    }>;
  };
};

const OMEN_QUERY = `
query OmenMarkets($first: Int!) {
  fixedProductMarketMakers(
    first: $first
    where: {isPendingArbitration: false}
    orderBy: creationTimestamp
    orderDirection: desc
  ) {
    id
    title
    outcomes
    outcomeTokenMarginalPrices
    collateralVolumeUSD
  }
}
`;

export async function fetchGnosisMarkets(limit = 50): Promise<ExternalMarket[]> {
  const endpoint =
    process.env.GNOSIS_OMEN_SUBGRAPH_URL ??
    "https://api.thegraph.com/subgraphs/name/protofire/omen-xdai";

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      query: OMEN_QUERY,
      variables: { first: limit }
    })
  });

  if (!res.ok) {
    throw new Error(`Gnosis/Omen subgraph request failed with status ${res.status}`);
  }

  const json = (await res.json()) as OmenResponse;
  const rows = json.data?.fixedProductMarketMakers ?? [];

  return rows
    .map((m) => {
      const prices = m.outcomeTokenMarginalPrices ?? [];
      if (prices.length < 2) return null;

      const yes = Number(prices[0]);
      const no = Number(prices[1]);
      if (Number.isNaN(yes) || Number.isNaN(no)) return null;

      return {
        id: m.id,
        question: m.title ?? "",
        yesPrice: yes,
        noPrice: no,
        liquidityUsd: Number(m.collateralVolumeUSD ?? 0),
        source: "gnosis" as const
      };
    })
    .filter((m): m is ExternalMarket => Boolean(m?.id && m.question));
}
