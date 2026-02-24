import type { FastifyInstance } from "fastify";
import { z } from "zod";

import { db } from "../storage";
import { verifyApiKey } from "../services/auth";
import { readCredentialFileRecord } from "../services/credentials";
import { executeTradeIntent } from "../services/execution";

const tradeSchema = z.object({
  agentId: z.string().min(3),
  marketId: z.string().min(3),
  side: z.enum(["YES", "NO"]),
  amountUsd: z.number().positive(),
  confidence: z.number().min(0).max(1),
  riskConfig: z
    .object({
      maxPositionUsd: z.number().positive().optional(),
      maxSpreadBps: z.number().positive().optional(),
      maxDailyUsd: z.number().positive().optional()
    })
    .optional()
});

export async function tradeRoute(app: FastifyInstance) {
  app.post("/trade", async (request, reply) => {
    const body = tradeSchema.parse(request.body);
    const apiKey = request.headers["x-api-key"];

    if (!db.accounts.has(body.agentId)) {
      return reply.code(404).send({ ok: false, error: "Agent not registered" });
    }

    if (typeof apiKey !== "string" || apiKey.length < 20) {
      return reply.code(401).send({ ok: false, error: "Missing or invalid x-api-key header" });
    }

    const credential = await readCredentialFileRecord(body.agentId);
    if (!credential || !verifyApiKey(apiKey, credential.apiKeyHash)) {
      return reply.code(401).send({ ok: false, error: "Invalid API key" });
    }

    let result;
    try {
      result = await executeTradeIntent(body);
    } catch (error) {
      return reply.code(502).send({ ok: false, error: (error as Error).message });
    }
    if (!result.ok) {
      return reply.code(result.status).send({ ok: false, error: result.error, market: result.market });
    }

    return reply.send({ ok: true, receipt: result.receipt, market: result.market, risk: result.riskConfig });
  });
}
