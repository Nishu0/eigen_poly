export type Chain = "polygon" | "solana";

export type AgentAccount = {
  agentId: string;
  walletAddress: string;
  safeAddress?: string;
  solanaVault?: string;
  createdAt: string;
};

export type RiskConfig = {
  maxPositionUsd?: number;
  maxSpreadBps?: number;
  maxDailyUsd?: number;
};

export type TradeIntent = {
  marketId: string;
  side: "YES" | "NO";
  amountUsd: number;
  confidence: number;
  riskConfig?: RiskConfig;
};
