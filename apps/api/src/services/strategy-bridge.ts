const STRATEGY_BRIDGE_URL = process.env.STRATEGY_BRIDGE_URL ?? "http://127.0.0.1:8787";

type ArbitragePlanRequest = {
  limit?: number;
  totalTradeAmount?: number;
  minProfit?: number;
};

export async function fetchBridgeHealth() {
  const res = await fetch(`${STRATEGY_BRIDGE_URL}/health`);
  if (!res.ok) {
    throw new Error(`strategy bridge health failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchArbitragePlans(input: ArbitragePlanRequest) {
  const res = await fetch(`${STRATEGY_BRIDGE_URL}/strategies/arbitrage/plan`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      limit: input.limit ?? 50,
      total_trade_amount: input.totalTradeAmount ?? 10,
      min_profit: input.minProfit ?? 0.005
    })
  });

  if (!res.ok) {
    throw new Error(`strategy bridge arbitrage plan failed with status ${res.status}`);
  }

  return res.json();
}
