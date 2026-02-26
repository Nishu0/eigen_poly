# EigenPoly Skills

## Project Goal

Build a secure, dynamic, production-grade multi-agent trading system that:
- Uses Eigen Compute for verifiable intent-to-action execution
- Trades on Polymarket via Polygon Safe flows
- Allocates and rotates capital into Solana DeFi vault strategies
- Avoids static hardcoded trading logic and uses dynamic market + risk inputs

## Canonical Credentials Storage

Store the API key in **one canonical location**:

- `credentials.json`

```json
{
  "agents": {
    "<agent_id>": {
      "api_key": "<issued_api_key>",
      "wallet_address": "<0x...>",
      "polygon_safe": "<safe_address>",
      "solana_vault": "<vault_pubkey>",
      "created_at": "<iso_timestamp>",
      "scopes": ["trade", "balance", "markets"]
    }
  }
}
```

### Rules
- Never store production API keys in source code, `.env.example`, or logs
- Encrypt at rest when possible (OS keychain / KMS recommended)
- Rotate compromised keys immediately
- Use per-agent scoped keys and least-privilege permissions
- Use `EIGENPOLY_MASTER_KEY` (32-byte hex) for encryption at runtime
- `credentials.json` lives at `~/.eigenpoly/credentials.json` in production

---

## Agent Flow

```
Register → API-Key (wallet signing) → Compute → Polygon Safe (Polymarket)
                                                        ↓
                                                 Solana DeFi Vaults
```

1. **Register** — agent submits `agentId`, `walletAddress`, `signature`
2. **API-Key Issuance** — server verifies wallet ownership via EIP-191 signature, generates scoped API key
3. **Production Accounts** — Polygon Safe + Solana vault profile created/linked for the agent
4. **Store credentials** — agent stores the issued API key in `credentials.json`
5. **Compute** — intent compile/verification via Eigen Compute before execution
6. **Execution routing:**
   - **Polygon Safe** → Polymarket (prediction market trades)
   - **Solana DeFi Vaults** → capital strategy (yield, rebalancing)
7. **Record** — receipts, PnL, and risk state persisted per agent

---

## Backend Routes

### 1. Register Route

`POST /register`

Onboard agent, verify wallet ownership, issue scoped API credentials, generate production accounts.

**Request:**
```json
{
  "agentId": "agent-001",
  "walletAddress": "0xAbC...123",
  "signature": "0x..."
}
```

**Response:**
```json
{
  "status": "registered",
  "agentId": "agent-001",
  "apiKey": "epk_a1b2c3d4...",
  "credentialStore": "~/.eigenpoly/credentials.json",
  "accounts": {
    "polygonSafe": "0x...",
    "solanaVault": "So1..."
  }
}
```

> ⚠️ `apiKey` is shown **once** at registration. Store it in `credentials.json` immediately.

---

### 2. Balance Route

`GET /balance/{agent_id}`

Fetch aggregate and per-chain balances for an agent.

**Headers:** `x-api-key: <api_key>`

**Response:**
```json
{
  "agentId": "agent-001",
  "polygon": {
    "pol": 1.25,
    "usdc_e": 500.0
  },
  "solana": {
    "sol": 0.0,
    "vault_balance_usd": 0.0
  },
  "total_usd": 500.0
}
```

---

### 3. Trade Route

`POST /trade`

Execute a market-aware trade for an agent. Requires `marketId` (or market reference) to identify which Polymarket market to trade on.

**Headers:** `x-api-key: <api_key>`

**Request:**
```json
{
  "agentId": "agent-001",
  "marketId": "0x1234...abcd",
  "side": "YES",
  "amountUsd": 50.0,
  "riskConfig": {
    "maxSlippage": 0.05,
    "maxPositionPct": 0.10
  }
}
```

**Behavior:**
1. Validate market exists + check liquidity + slippage constraints via Gamma API
2. Run policy/risk checks in Eigen Compute
3. Execute via Polygon Safe (Polymarket split+CLOB flow)
4. Optionally rebalance to Solana vault strategy
5. Return execution receipt

**Response:**
```json
{
  "status": "executed",
  "tradeId": "trd_...",
  "market": "Will X happen?",
  "side": "YES",
  "amountUsd": 50.0,
  "entryPrice": 0.72,
  "tokensReceived": 69.44,
  "executionProof": "...",
  "postTradeBalance": { "usdc_e": 450.0 }
}
```

---

### 4. Market Routes

#### `GET /markets/trending`

Fetch live trending Polymarket markets by volume. No auth required.

**Query params:** `limit` (default 20)

#### `GET /markets/search?q={query}`

Search Polymarket markets by keyword. No auth required.

**Query params:** `q` (required), `limit` (default 20)

#### `GET /markets/{market_id}`

Get full details for a single Polymarket market.

#### `GET /markets/analysis`

Aggregate market analysis for agent decisioning — top volume markets with liquidity scores, price movements, and opportunity signals.

**Query params:** `limit` (default 10)

---

### 5. Agent Operations

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/register` | POST | signature | Register agent + issue API key |
| `/balance/{agent_id}` | GET | api-key | Aggregate balances |
| `/trade` | POST | api-key | Execute trade with market ID |
| `/markets/trending` | GET | none | Trending markets |
| `/markets/search` | GET | none | Search markets |
| `/markets/{market_id}` | GET | none | Market details |
| `/markets/analysis` | GET | none | Market analysis |
| `/agents/{agent_id}/trades` | GET | api-key | Trade history |
| `/agents/top` | GET | none | Top agents by PnL |
| `/agents/{agent_id}/copy` | POST | api-key | Copy-trade from top agents |

---

## Environment Variables

All required `.env` variables for the backend:

| Variable | Required | Description |
|----------|----------|-------------|
| `CHAINSTACK_NODE` | Yes | Polygon RPC URL (e.g. Chainstack, Alchemy, Infura) |
| `POLYCLAW_PRIVATE_KEY` | Yes (trading) | EVM private key for trade execution (hex, with/without 0x) |
| `EIGENPOLY_MASTER_KEY` | Yes (production) | 32-byte hex key for encrypting credentials at rest |
| `OPENROUTER_API_KEY` | Yes (analysis) | OpenRouter API key for LLM-powered market analysis/hedge discovery |
| `HTTPS_PROXY` | Recommended | Rotating residential proxy for CLOB (e.g. IPRoyal) |
| `CLOB_MAX_RETRIES` | No | Max CLOB retries with IP rotation (default: 5) |
| `SOLANA_RPC_URL` | Yes (Solana) | Solana RPC endpoint for vault operations |
| `SOLANA_PRIVATE_KEY` | Yes (Solana) | Solana wallet private key for DeFi vault operations |
| `STRATEGY_BRIDGE_URL` | No | URL for MCP strategy server (Python backend) |
| `AGENT_STORE_PATH` | No | Path to agent store JSON file (default: `~/.eigenpoly/agents.json`) |
| `CREDENTIALS_PATH` | No | Path to credentials file (default: `~/.eigenpoly/credentials.json`) |

### Example `.env`

```bash
# Required — Polygon
CHAINSTACK_NODE=https://polygon-mainnet.core.chainstack.com/YOUR_KEY
POLYCLAW_PRIVATE_KEY=0xYOUR_PRIVATE_KEY

# Required — Security
EIGENPOLY_MASTER_KEY=0x0000000000000000000000000000000000000000000000000000000000000000

# Required — Analysis
OPENROUTER_API_KEY=sk-or-v1-...

# Optional — Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=BASE58_ENCODED_KEY

# Optional — Proxy
HTTPS_PROXY=http://user:pass@geo.iproyal.com:12321
CLOB_MAX_RETRIES=10

# Optional — Paths
AGENT_STORE_PATH=~/.eigenpoly/agents.json
CREDENTIALS_PATH=~/.eigenpoly/credentials.json
```

---

## Portfolio and Strategy Lifecycle

- **Money Path:** EVM capital → Solana swap → DeFi strategies → rebalance back for Polymarket opportunities
- **Dynamic allocation:** updates per volatility, confidence, drawdown, and liquidity
- **Safety controls:** max position size, per-market exposure cap, daily loss cap, cooldown after consecutive losses

## Security and Compliance

- Wallet-signature auth for API key issuance (EIP-191)
- Scoped API keys with per-agent permissions
- Strict allowlists for executable actions
- Auditable receipts for each step
- No secret leakage in logs
- Per-route rate limits and replay protection
- Deterministic policy checks before execution

## Build Principles

- No static trading rules
- All execution decisions are policy-bound and dynamically computed
- Every action must be explainable, logged, and reproducible via receipt trail
- Market reads must come from live providers (Polymarket + Gnosis/Omen), not seeded synthetic prices
