import type { FastifyInstance } from "fastify";
import { z } from "zod";

import { fetchArbitragePlans, fetchBridgeHealth } from "../services/strategy-bridge";

const planSchema = z.object({
  limit: z.number().int().positive().max(500).optional(),
  totalTradeAmount: z.number().positive().optional(),
  minProfit: z.number().positive().max(0.25).optional()
});

export async function strategyRoutes(app: FastifyInstance) {
  app.get("/mcp/health", async (_req, reply) => {
    try {
      const health = await fetchBridgeHealth();
      return reply.send({ ok: true, bridge: health });
    } catch (error) {
      return reply.code(502).send({ ok: false, error: (error as Error).message });
    }
  });

  app.post("/mcp/strategies/arbitrage/plan", async (request, reply) => {
    const body = planSchema.parse(request.body ?? {});

    try {
      const data = await fetchArbitragePlans(body);
      return reply.send(data);
    } catch (error) {
      return reply.code(502).send({ ok: false, error: (error as Error).message });
    }
  });
}
