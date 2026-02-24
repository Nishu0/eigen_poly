import type { AgentAccount, TradeIntent } from "./types";

const accounts = new Map<string, AgentAccount>();
const balances = new Map<string, { polygonUsd: number; solanaUsd: number }>();
const trades: Array<TradeIntent & { agentId: string; createdAt: string; pnlUsd: number }> = [];
const copyTrading = new Map<string, { sourceAgentId: string; riskMultiplier: number; maxDailyUsd: number }>();

export const db = {
  accounts,
  balances,
  trades,
  copyTrading
};
