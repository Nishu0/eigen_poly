import type { FastifyInstance } from "fastify";
import { z } from "zod";

import { CREDENTIALS_PATH } from "../config";
import { db } from "../storage";
import { hashApiKey, hashSignature, issueApiKey } from "../services/auth";
import { upsertCredentialRecord } from "../services/credentials";

const registerSchema = z.object({
  agentId: z.string().min(3),
  walletAddress: z.string().min(10),
  signature: z.string().min(32)
});

export async function registerRoute(app: FastifyInstance) {
  app.post("/register", async (request, reply) => {
    const body = registerSchema.parse(request.body);
    const apiKey = issueApiKey();
    const signatureHash = hashSignature(body.signature);
    const apiKeyHash = hashApiKey(apiKey);

    db.accounts.set(body.agentId, {
      agentId: body.agentId,
      walletAddress: body.walletAddress,
      safeAddress: "polygon-safe-pending",
      solanaVault: "solana-vault-pending",
      createdAt: new Date().toISOString()
    });

    db.balances.set(body.agentId, { polygonUsd: 0, solanaUsd: 0 });
    let credentials;
    try {
      credentials = await upsertCredentialRecord({
        agentId: body.agentId,
        walletAddress: body.walletAddress,
        signatureHash,
        apiKey,
        apiKeyHash
      });
    } catch (error) {
      return reply.code(500).send({
        ok: false,
        error: "Failed to persist encrypted credentials",
        detail: (error as Error).message
      });
    }

    return reply.send({
      ok: true,
      agentId: body.agentId,
      message: "Registration accepted. Credentials persisted in canonical location.",
      credentialsPath: CREDENTIALS_PATH,
      credentialsAbsolutePath: credentials.absolutePath,
      apiKey,
      security: {
        keyStorage: "encrypted-aes-256-gcm",
        signatureBound: true
      }
    });
  });
}
