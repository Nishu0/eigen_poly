# Eigen Poly Monorepo

Turbo + Bun workspace for:
- `apps/web`: Next.js app using shadcn-style UI primitives from `packages/ui`
- `apps/api`: Fastify backend for agent registration, balance, market analysis, and trade execution workflows
- `packages/ui`: shared UI package

## Quick start

```bash
export EIGENPOLY_MASTER_KEY=$(openssl rand -base64 32)
# Optional custom live feeds
# export POLYMARKET_GAMMA_BASE_URL=https://gamma-api.polymarket.com
# export GNOSIS_OMEN_SUBGRAPH_URL=https://api.thegraph.com/subgraphs/name/protofire/omen-xdai
# Strategy MCP bridge (Python service)
# export STRATEGY_BRIDGE_URL=http://127.0.0.1:8787
bun install
bun run dev
```

## App ports
- Web: `http://localhost:3000`
- API: `http://localhost:3001`

## Security
- Canonical credentials file: `~/.eigenpoly/credentials.json`
- API keys are encrypted with AES-256-GCM using `EIGENPOLY_MASTER_KEY`
- `POST /register` issues an API key and stores encrypted credential metadata
- `POST /trade` requires `x-api-key` and runs dynamic market + risk checks before execution

## Live market + strategy endpoints
- `GET /markets/unified?limit=50` -> live Polymarket + Gnosis/Omen markets
- `POST /mcp/strategies/arbitrage/plan` -> invokes Python strategy MCP bridge
- `GET /mcp/health` -> validates strategy bridge connectivity

Python strategy backend docs:
- [python/strategy_mcp/README.md](/Users/nisargthakkar/Projects/eigen_poly/python/strategy_mcp/README.md)
