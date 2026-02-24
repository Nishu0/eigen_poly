import cors from "@fastify/cors";
import Fastify from "fastify";

import { balanceRoute } from "./routes/balance";
import { marketsRoute } from "./routes/markets";
import { registerRoute } from "./routes/register";
import { strategyRoutes } from "./routes/strategies";
import { tradeRoute } from "./routes/trade";

const app = Fastify({ logger: true });

await app.register(cors, {
  origin: true
});

app.get("/health", async () => ({ ok: true }));

await registerRoute(app);
await balanceRoute(app);
await tradeRoute(app);
await marketsRoute(app);
await strategyRoutes(app);

const port = Number(process.env.PORT ?? 3001);
const host = process.env.HOST ?? "0.0.0.0";

app.listen({ port, host }).catch((error) => {
  app.log.error(error);
  process.exit(1);
});
