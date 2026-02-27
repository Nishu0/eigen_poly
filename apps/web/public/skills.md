---
name: eigenpoly
description: "Trade on Polymarket prediction markets via TEE-secured wallets. Browse markets, place bets, track positions with live P&L. Powered by EigenCompute."
metadata: {"openclaw":{"emoji":"🔮","homepage":"https://136.117.112.168:8000","primaryEnv":"EIGENPOLY_API_KEY","requires":{"env":["EIGENPOLY_API_KEY"]}}}
---

# EigenPoly

Polymarket prediction market trading skill. Browse markets, place bets (YES/NO), track positions with live P&L — all secured by **EigenCompute TEE** (Intel TDX).

> 🔐 **Agent wallets run inside a Trusted Execution Environment.** Private keys are hardware-isolated — even the server operator cannot access them. [Verify attestation →](https://verify.eigencloud.xyz/app/0xfE82CD3c9C2702f3bB6b1617ABF2aABa8b343260)

## Credential Storage

Store the API key in **one canonical location**:

- `~/.eigenpoly/credentials.json`

```json
{
  "apiKey": "epk_...",
  "agentId": "my-agent-001"
}
```

Environment export:
```bash
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

## Base URL & Auth

- **Base URL**: `https://136.117.112.168:8000`
- **Auth header**: `x-api-key: <EIGENPOLY_API_KEY>`
- **Content-Type**: `application/json`

```bash
export EIGENPOLY_API_URL="https://136.117.112.168:8000"
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

## Getting Started

### 1. Register your agent

Just provide a name. The TEE generates a dedicated wallet for you.

```bash
curl -X POST "$EIGENPOLY_API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{"agentId": "my-agent-001"}'
```

**Response:**
```json
{
  "status": "registered",
  "agentId": "my-agent-001",
  "apiKey": "epk_a1b2c3...",
  "walletAddress": "0xTEE...Derived",
  "walletMode": "tee",
  "credentialStore": "~/.eigenpoly/credentials.json"
}
```

> ⚠️ The `apiKey` is shown **once**. Store it immediately.

### 2. Store your credentials

```bash
mkdir -p ~/.eigenpoly
cat > ~/.eigenpoly/credentials.json <<EOF
{
  "apiKey": "epk_a1b2c3...",
  "agentId": "my-agent-001"
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

| Route | Method | Description |
|-------|--------|-------------|
| `GET /markets/trending?limit=20` | GET | Trending markets by 24h volume |
| `GET /markets/search?q={query}` | GET | Search markets by keyword |
| `GET /markets/{market_id}` | GET | Full details for a single market |
| `GET /markets/analysis?limit=10` | GET | Market analysis with opportunity signals |

**Market response fields:** `id`, `question`, `slug`, `yes_price`, `no_price`, `volume`, `volume_24h`, `liquidity`, `end_date`, `active`, `closed`, `resolved`, `outcome`.

**Analysis signals:** `liquidity_score` (HIGH/MEDIUM/LOW), `opportunity_signal` (STRONG/MODERATE/VOLUME_SPIKE/NEUTRAL), `spread`.

---

### Trade Route (Auth Required)

#### `POST /trade`

Place a bet on Polymarket. The TEE signs the on-chain transaction — your private key never leaves the enclave.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `agentId` | string | Yes | Your agent ID |
| `marketId` | string | Yes | Polymarket market ID |
| `side` | string | Yes | `"YES"` or `"NO"` |
| `amountUsd` | float | Yes | USD amount to bet |
| `skipClobSell` | bool | No | Skip selling unwanted side |
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

---

### Agent Routes (Auth Required)

| Route | Method | Description |
|-------|--------|-------------|
| `GET /balance/{agent_id}` | GET | Per-chain balances (Polygon, Solana) |
| `GET /agents/{agent_id}/positions` | GET | Open positions with **live P&L** |
| `GET /agents/{agent_id}/trades?limit=50` | GET | Full trade history |
| `GET /agents/{agent_id}/pnl` | GET | Aggregate P&L summary |

**P&L response:**
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

## Full Route Summary

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/register` | POST | none | Register agent, get API key + TEE wallet |
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

1. **Register** — `POST /register` → get API key + TEE-derived wallet
2. **Search** — `GET /markets/search?q=bitcoin`
3. **Analyze** — `GET /markets/analysis`
4. **Bet** — `POST /trade` with marketId + side + amount
5. **Monitor** — `GET /agents/{id}/positions` (live P&L)
6. **Review** — `GET /agents/{id}/pnl`

## Security & Trust

- **TEE-isolated wallets** — private keys exist only inside Intel TDX enclave
- **Verifiable build** — [verify the exact Docker image running](https://verify.eigencloud.xyz/app/0xfE82CD3c9C2702f3bB6b1617ABF2aABa8b343260)
- **HD derivation** — each agent gets a unique wallet from `m/44'/60'/0'/0/{index}`
- **No key storage** — DB stores only the derivation index (an integer)
- **API keys are SHA-256 hashed** — raw keys never persisted
- **EigenLayer backed** — cryptographic attestation proves code integrity
