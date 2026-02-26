---
name: eigenpoly
description: "Trade on Polymarket prediction markets. Browse markets, place bets, track positions with live P&L, manage balances. Polygon/Web3."
metadata: {"openclaw":{"emoji":"🔮","homepage":"https://eigenpoly.com","primaryEnv":"EIGENPOLY_API_KEY","requires":{"env":["EIGENPOLY_API_KEY"]}}}
---

# EigenPoly

Polymarket prediction market trading skill. Browse markets, place bets (YES/NO), track positions with live P&L, and manage agent wallets.

## Standard credential storage (required)

Store the API key in **one canonical location**:

- `~/.eigenpoly/credentials.json`

Recommended file contents:
```json
{
  "apiKey": "epk_...",
  "agentId": "my-agent-001",
  "walletAddress": "0xAbC...123"
}
```

Optional environment export (runtime convenience):
```bash
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

## Base URL & Auth

- Base URL: `https://backend-production-baaa.up.railway.app`
- Auth header: `x-api-key: <EIGENPOLY_API_KEY>`
- Content-Type: `application/json`

Quick env setup:
```bash
export EIGENPOLY_API_URL="https://backend-production-baaa.up.railway.app"
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

## Getting Started

### 1. Register your agent

Register to receive an API key. You must sign a message with your wallet to prove ownership.

```bash
curl -X POST "$EIGENPOLY_API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "my-agent-001",
    "walletAddress": "0xYourWalletAddress",
    "signature": "0xYourEIP191Signature"
  }'
```

**Response:**
```json
{
  "status": "registered",
  "agentId": "my-agent-001",
  "apiKey": "epk_a1b2c3...",
  "credentialStore": "~/.eigenpoly/credentials.json",
  "accounts": {
    "polygonSafe": "0x...",
    "solanaVault": "So1..."
  }
}
```

> ⚠️ The `apiKey` is shown **once**. Store it in `~/.eigenpoly/credentials.json` immediately.

The signing message format is: `EigenPoly Agent Registration: <agentId>`

### 2. Store your credentials

```bash
mkdir -p ~/.eigenpoly
cat > ~/.eigenpoly/credentials.json <<EOF
{
  "apiKey": "epk_a1b2c3...",
  "agentId": "my-agent-001",
  "walletAddress": "0xYourWalletAddress"
}
EOF
chmod 600 ~/.eigenpoly/credentials.json
```

### 3. Start trading

```bash
# Search for markets
curl "$EIGENPOLY_API_URL/markets/search?q=bitcoin"

# Place a bet
curl -X POST "$EIGENPOLY_API_URL/trade" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -d '{
    "agentId": "my-agent-001",
    "marketId": "558960",
    "side": "YES",
    "amountUsd": 10
  }'
```

---

## API Reference

### Market Routes (No Auth Required)

#### `GET /markets/trending`

Fetch trending Polymarket markets by 24h volume.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Number of markets (1–100) |

```bash
curl "$EIGENPOLY_API_URL/markets/trending?limit=5"
```

---

#### `GET /markets/search?q={query}`

Search markets by keyword.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `limit` | int | No | Results limit (default 20) |

```bash
curl "$EIGENPOLY_API_URL/markets/search?q=election&limit=10"
```

---

#### `GET /markets/{market_id}`

Get full details for a single market.

```bash
curl "$EIGENPOLY_API_URL/markets/558960"
```

**Response includes:** `id`, `question`, `slug`, `yes_price`, `no_price`, `volume`, `volume_24h`, `liquidity`, `end_date`, `active`, `closed`, `resolved`, `outcome`.

---

#### `GET /markets/analysis`

Aggregate market analysis with liquidity scores and opportunity signals.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 10 | Number of markets (1–50) |

**Response includes per market:** `liquidity_score` (HIGH/MEDIUM/LOW), `opportunity_signal` (STRONG/MODERATE/VOLUME_SPIKE/NEUTRAL), `spread`.

---

### Balance Route (Auth Required)

#### `GET /balance/{agent_id}`

Fetch aggregate per-chain balances.

```bash
curl "$EIGENPOLY_API_URL/balance/my-agent-001" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

**Response:**
```json
{
  "agentId": "my-agent-001",
  "polygon": { "pol": 1.25, "usdc_e": 500.0 },
  "solana": { "sol": 0.0, "vault_balance_usd": 0.0 },
  "total_usd": 500.0
}
```

---

### Trade Route (Auth Required)

#### `POST /trade`

Place a bet on a Polymarket prediction market. Executes a real on-chain trade via split + CLOB.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `agentId` | string | Yes | Your agent ID |
| `marketId` | string | Yes | Polymarket market ID |
| `side` | string | Yes | `"YES"` or `"NO"` |
| `amountUsd` | float | Yes | USD amount to bet |
| `skipClobSell` | bool | No | Skip selling unwanted side (default false) |
| `riskConfig.maxSlippage` | float | No | Max slippage (default 0.05) |

```bash
curl -X POST "$EIGENPOLY_API_URL/trade" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -d '{
    "agentId": "my-agent-001",
    "marketId": "558960",
    "side": "YES",
    "amountUsd": 10.0
  }'
```

**Response:**
```json
{
  "status": "executed",
  "tradeId": "trd_abc123...",
  "market": "Will X happen?",
  "side": "YES",
  "amountUsd": 10.0,
  "entryPrice": 0.72,
  "splitTx": "0x...",
  "clobOrderId": "...",
  "clobFilled": true,
  "positionId": "uuid..."
}
```

---

### Agent Routes (Auth Required)

#### `GET /agents/{agent_id}/positions`

Get all positions with live P&L calculated from current Polymarket prices.

```bash
curl "$EIGENPOLY_API_URL/agents/my-agent-001/positions" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

**Response includes per position:** `entry_price`, `current_price`, `pnl_usd`, `pnl_pct`, `status`.

---

#### `GET /agents/{agent_id}/trades`

Get full trade history.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results (1–200) |

```bash
curl "$EIGENPOLY_API_URL/agents/my-agent-001/trades?limit=10" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

---

#### `GET /agents/{agent_id}/pnl`

Get aggregate P&L summary.

```bash
curl "$EIGENPOLY_API_URL/agents/my-agent-001/pnl" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

**Response:**
```json
{
  "agentId": "my-agent-001",
  "total_invested": 100.0,
  "total_current_value": 115.50,
  "total_pnl_usd": 15.50,
  "total_pnl_pct": 15.50,
  "open_positions": 3,
  "total_trades": 7
}
```

---

## Route Summary

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/register` | POST | wallet signature | Register agent, get API key |
| `/balance/{agent_id}` | GET | `x-api-key` | Per-chain balances |
| `/trade` | POST | `x-api-key` | Place a bet on Polymarket |
| `/agents/{agent_id}/positions` | GET | `x-api-key` | Positions with live P&L |
| `/agents/{agent_id}/trades` | GET | `x-api-key` | Trade history |
| `/agents/{agent_id}/pnl` | GET | `x-api-key` | P&L summary |
| `/markets/trending` | GET | none | Trending markets |
| `/markets/search` | GET | none | Search markets |
| `/markets/{market_id}` | GET | none | Market details |
| `/markets/analysis` | GET | none | Market analysis + signals |
| `/health` | GET | none | Health check |
| `/docs` | GET | none | Interactive Swagger UI |

## Agent Trading Flow

1. **Search** — find markets: `GET /markets/search?q=bitcoin`
2. **Analyze** — check liquidity/signals: `GET /markets/analysis`
3. **Bet** — place a trade: `POST /trade` with marketId + side + amount
4. **Monitor** — check positions: `GET /agents/{id}/positions` (includes live P&L)
5. **Review** — check overall performance: `GET /agents/{id}/pnl`

## Security

- API keys are hashed (SHA-256) before storage — raw keys are never persisted
- Wallet signature verification via EIP-191 for registration
- All trade/balance/position routes require valid `x-api-key` header
- Keep only small amounts in the trading wallet
