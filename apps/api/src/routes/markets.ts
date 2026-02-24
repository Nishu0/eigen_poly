import type { FastifyInstance } from "fastify";
import { z } from "zod";

import { db } from "../storage";
import { fetchUnifiedMarkets, getMarketAnalysis } from "../services/market";

export async function marketsRoute(app: FastifyInstance) {
  app.get("/markets/analysis", async () => {
    const analysis = await getMarketAnalysis();
    return {
      ok: true,
      tabs: analysis.tabs,
      engine: analysis.engine,
      status: analysis.status
    };
  });

  app.get("/markets/tabs", async () => {
    return {
      ok: true,
      tabs: [
        { id: "trending", label: "Trending" },
        { id: "mispriced", label: "Mispriced" },
        { id: "high-volume", label: "High Volume" },
        { id: "agent-picks", label: "Agent Picks" }
      ]
    };
  });

  app.get("/markets/unified", async (request, reply) => {
    const query = z.object({ limit: z.coerce.number().int().positive().max(500).optional() }).parse(request.query);

    try {
      const unified = await fetchUnifiedMarkets(query.limit ?? 50);
      return {
        ok: true,
        markets: {
          polymarket: unified.polymarket,
          gnosis: unified.gnosis
        },
        errors: unified.errors
      };
    } catch (error) {
      return reply.code(502).send({ ok: false, error: (error as Error).message });
    }
  });

  app.get("/agents/top", async () => {
    const grouped = new Map<string, number>();

    for (const trade of db.trades) {
      grouped.set(trade.agentId, (grouped.get(trade.agentId) ?? 0) + trade.pnlUsd);
    }

    const leaderboard = [...grouped.entries()]
      .map(([agentId, pnlUsd]) => ({ agentId, pnlUsd: Number(pnlUsd.toFixed(2)) }))
      .sort((a, b) => b.pnlUsd - a.pnlUsd)
      .slice(0, 10);

    return { ok: true, leaderboard };
  });

  app.get("/agents/:agentId/trades", async (request, reply) => {
    const { agentId } = request.params as { agentId: string };
    if (!db.accounts.has(agentId)) {
      return reply.code(404).send({ ok: false, error: "Agent not registered" });
    }

    return {
      ok: true,
      trades: db.trades.filter((trade) => trade.agentId === agentId)
    };
  });

  app.post("/agents/:agentId/copy", async (request, reply) => {
    const params = z.object({ agentId: z.string().min(3) }).parse(request.params);
    const body = z
      .object({
        sourceAgentId: z.string().min(3),
        riskMultiplier: z.number().positive().max(2).default(1),
        maxDailyUsd: z.number().positive().default(100)
      })
      .parse(request.body);

    if (!db.accounts.has(params.agentId)) {
      return reply.code(404).send({ ok: false, error: "Follower agent not registered" });
    }
    if (!db.accounts.has(body.sourceAgentId)) {
      return reply.code(404).send({ ok: false, error: "Source agent not registered" });
    }

    db.copyTrading.set(params.agentId, body);
    return { ok: true, followerAgentId: params.agentId, config: body };
  });
}
