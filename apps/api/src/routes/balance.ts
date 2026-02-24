import type { FastifyInstance } from "fastify";

import { db } from "../storage";

export async function balanceRoute(app: FastifyInstance) {
  app.get("/balance/:agentId", async (request, reply) => {
    const { agentId } = request.params as { agentId: string };
    const account = db.accounts.get(agentId);

    if (!account) {
      return reply.code(404).send({ ok: false, error: "Agent not registered" });
    }

    const balance = db.balances.get(agentId) ?? { polygonUsd: 0, solanaUsd: 0 };

    return reply.send({
      ok: true,
      agentId,
      chains: {
        polygon: balance.polygonUsd,
        solana: balance.solanaUsd
      },
      totalUsd: balance.polygonUsd + balance.solanaUsd
    });
  });
}
