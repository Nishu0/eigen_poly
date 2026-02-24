# Eigen Poly Skills

## Project Goal
Build a secure, dynamic, production-grade multi-agent trading system that:
- Uses Eigen Compute for verifiable intent-to-action execution
- Trades on Polymarket via Polygon Safe flows
- Allocates and rotates capital into Solana DeFi vault strategies
- Avoids static hardcoded trading logic and uses dynamic market + risk inputs
- Follows patterns inspired by:
  - https://github.com/gnosis/prediction-market-agent/tree/main

## Canonical Credentials Storage
Store the API key in **one canonical location**:

- `~/.eigenpoly/credentials.json`

Rules:
- Never store production API keys in source code, `.env.example`, or logs
- Encrypt at rest when possible (OS keychain/KMS recommended)
- Rotate compromised keys immediately
- Use per-agent scoped keys and least-privilege permissions
- Use `EIGENPOLY_MASTER_KEY` (32-byte key) for encryption at runtime

## Agent Flow
1. Register agent and wallet identity
2. API-key authentication via wallet signing
3. Intent compile/verification via Eigen Compute
4. Execution routing:
   - Polygon Safe (Polymarket execution path)
   - Solana DeFi vaults (capital strategy path)
5. Record receipts, PnL, and risk state

## Core Agent Routes

### 1) Register Route
`POST /register`
- Purpose: onboard agent, verify wallet ownership, issue scoped API credentials
- Input:
  - `agentId`
  - `walletAddress`
  - `signature` (wallet signature for API-key issuance)
- Output:
  - registration status
  - issued `apiKey` (shown once at registration)
  - credential metadata pointer (`~/.eigenpoly/credentials.json`)
  - account linkage (Polygon Safe + Solana vault profile)

### 2) Balance Route
`GET /balance/:agentId`
- Purpose: fetch aggregate and per-chain balances
- Includes:
  - Polygon Safe balances (USDC and collateral)
  - Solana vault balances and available capital
  - computed total USD exposure

### 3) Trade Route
`POST /trade`
- Purpose: execute market-aware trade for an agent
- Input:
  - `x-api-key` header
  - `agentId`
  - `marketId` (or market reference)
  - `side` (YES/NO)
  - `amountUsd`
  - `riskConfig`
- Behavior:
  - validate market + liquidity + slippage constraints
  - run policy/risk checks in Eigen Compute
  - execute via Polygon Safe (Polymarket)
  - optionally rebalance to Solana vault strategy
- Output:
  - trade receipt
  - execution proof/trace
  - post-trade balance + PnL delta

## Routes for Agent Operations
- `GET /markets/analysis`
  - Market Analysis for agent decisioning
- `GET /balance/:agentId`
  - Check Balance
- `GET /markets/tabs`
  - Markets Tabs / filtered discovery views
- `POST /trade`
  - Agents Trade
- `GET /agents/:agentId/trades`
  - Full trade history for each agent
- `GET /agents/top`
  - Top agents by PnL for copy-trading
- `POST /agents/:agentId/copy`
  - Enable copy-trade from selected top agents with limits

## Portfolio and Strategy Lifecycle
- Ideal Money Path:
  - EVM capital -> Solana swap -> DeFi strategies -> rebalance back for Polymarket opportunities
- Dynamic allocation engine:
  - updates per volatility, confidence, drawdown, and liquidity
- Safety controls:
  - max position size
  - per-market exposure cap
  - daily loss cap
  - cooldown after consecutive losses

## Agent PnL, Trades, and Copy Trading
- Track for every agent:
  - realized/unrealized PnL
  - win-rate and drawdown
  - market category performance
  - execution quality (slippage and fill speed)
- Copy trading:
  - allow agents to copy top agents
  - enforce follower risk multipliers and caps
  - support opt-in/opt-out with transparent fee rules

## Notifications
Telegram daily updates to users including:
- trade history summary
- daily PnL
- market analysis highlights
- risk alerts and exposure report

## Security and Compliance Baseline
- Wallet-signature auth for API key issuance
- strict allowlists for executable actions
- auditable receipts for each step
- no secret leakage in logs
- per-route rate limits and replay protection
- deterministic policy checks before execution

## Build Principles
- No static trading rules
- All execution decisions are policy-bound and dynamically computed
- Every action must be explainable, logged, and reproducible via receipt trail
- Market reads must come from live providers (Polymarket + Gnosis/Omen), not seeded synthetic prices

## MCP Strategy Backend
- Python MCP server provides strategy tools for agents:
  - `polymarket_markets`
  - `gnosis_markets`
  - `unified_markets`
  - `arbitrage_plans`
- Fastify integrates through `STRATEGY_BRIDGE_URL` and exposes:
  - `GET /mcp/health`
  - `POST /mcp/strategies/arbitrage/plan`
