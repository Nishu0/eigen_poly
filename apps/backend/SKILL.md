---
name: eigenpoly
description: "trade on polymarket prediction markets. browse markets, place bets, track positions with live p&l, check multi-chain balances (polygon/solana/base), access smart money analytics via metengine x402, check defi vault yields on base. eigencompute tee-secured."
metadata: {"openclaw":{"emoji":"🔮","homepage":"https://eigenpoly.xyz","primaryEnv":"EIGENPOLY_API_KEY","requires":{"env":["EIGENPOLY_API_KEY"]}}}
---

# eigenpoly skill

polymarket prediction market trading. browse markets, place bets (yes/no), track positions with live p&l, manage multi-chain balances, and access smart money analytics.

## rules — read before every action

- **never construct, guess, or reuse addresses.** wallet addresses, safe addresses, and deposit addresses must always come from an api response. call the endpoint and use what it returns.
- **never fabricate api responses.** if a call fails, report the error. do not invent plausible-looking data.
- **always call `POST /deposit/address` before giving a deposit address.** do not reuse one from a previous turn or a previous session.
- **always call `GET /balance/{agent_id}` before reporting balances.** do not recall or estimate balances.
- **never skip api calls to save time.** the user needs real data, not approximations.

## credential storage

store the api key in one canonical location:

```
~/.eigenpoly/credentials.json
```

```json
{
  "apiKey": "epk_...",
  "agentId": "my-agent-001"
}
```

optional env export:
```bash
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

## base url and auth

- base url: `https://api.eigenpoly.xyz`
- auth header: `x-api-key: <EIGENPOLY_API_KEY>`
- content-type: `application/json`

```bash
export EIGENPOLY_API_URL="https://api.eigenpoly.xyz"
export EIGENPOLY_API_KEY="$(jq -r .apiKey ~/.eigenpoly/credentials.json)"
```

---

## getting started

### 1. register your agent

```bash
curl -X POST "$EIGENPOLY_API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{"agentId": "my-agent-001"}'
```

response:
```json
{
  "status": "registered",
  "agentId": "my-agent-001",
  "apiKey": "epk_a1b2c3...",
  "walletAddress": "0x...",
  "safeWalletAddress": "0x...",
  "solanaAddress": "8B9aLD...",
  "walletType": "EOA + Safe + Solana vault",
  "walletMode": "tee",
  "claimCode": "ABCD-1234",
  "claimUrl": "https://www.eigenpoly.xyz/device?code=ABCD-1234",
  "fundingInfo": {
    "polygon_eoa": "0x...",
    "polygon_safe": "0x...",
    "solana_vault": "8B9aLD...",
    "note": "fund polygon eoa with usdc.e for trading. fund solana vault with usdc for metengine x402 calls."
  }
}
```

the apiKey is shown **once**. store it immediately.

three wallets are derived from the tee mnemonic:
- **polygon eoa** — trading signer, fund with usdc.e on polygon
- **polygon safe** — polymarket proxy wallet
- **solana vault** — fund with usdc on solana mainnet for metengine x402 payments

### 2. store credentials

```bash
mkdir -p ~/.eigenpoly
cat > ~/.eigenpoly/credentials.json <<EOF
{"apiKey": "epk_a1b2c3...", "agentId": "my-agent-001"}
EOF
chmod 600 ~/.eigenpoly/credentials.json
```

### 3. claim the agent (link to google account)

open the `claimUrl` from the registration response in a browser. sign in with google. the agent is now linked to the account and shows in the dashboard.

---

## api reference

### registration

#### `POST /register`

| param | type | description |
|-------|------|-------------|
| `agentId` | string | unique name for this agent |

---

### balance (multi-chain)

#### `GET /balance/{agent_id}`

returns balances across all chains. always check this first before trading or using metengine.

```bash
curl "$EIGENPOLY_API_URL/balance/my-agent-001" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

response:
```json
{
  "agentId": "my-agent-001",
  "polygon_eoa":  { "chain": "polygon", "chain_logo": "...", "address": "0x...", "native": 1.25, "native_symbol": "POL", "usdc": 500.0, "usdc_logo": "..." },
  "polygon_safe": { "chain": "polygon", "chain_logo": "...", "address": "0x...", "native": 0.0, "native_symbol": "POL", "usdc": 0.0,   "usdc_logo": "..." },
  "solana_vault": { "chain": "solana",  "chain_logo": "...", "address": "8B9...", "native": 0.05, "native_symbol": "SOL", "usdc": 2.5, "usdc_logo": "..." },
  "base_eoa":     { "chain": "base",    "chain_logo": "...", "address": "0x...", "native": 0.0, "native_symbol": "ETH", "usdc": 0.0,   "usdc_logo": "..." },
  "total_usdc": 502.5,
  "flags": { "auto_rebalance": false, "auto_freemonies": false }
}
```

---

### trading

#### `POST /trade`

executes an on-chain trade: splits usdc into yes+no tokens, sells the unwanted side via clob.

| param | type | required | description |
|-------|------|----------|-------------|
| `agentId` | string | yes | your agent id |
| `marketId` | string | yes | polymarket market id |
| `side` | string | yes | `"YES"` or `"NO"` |
| `amountUsd` | float | yes | usd amount |
| `skipClobSell` | bool | no | keep both token sides (default false) |
| `riskConfig.maxSlippage` | float | no | max slippage (default 0.05) |

```bash
curl -X POST "$EIGENPOLY_API_URL/trade" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -d '{"agentId": "my-agent-001", "marketId": "558960", "side": "YES", "amountUsd": 10}'
```

response:
```json
{
  "status": "executed",
  "tradeId": "trd_abc123",
  "market": "will X happen?",
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

### agent routes

#### `GET /agents/{agent_id}/positions`

positions with live p&l from current polymarket prices.

```bash
curl "$EIGENPOLY_API_URL/agents/my-agent-001/positions" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

#### `GET /agents/{agent_id}/trades?limit=50`

trade history. max limit 200.

#### `GET /agents/{agent_id}/pnl`

aggregate p&l summary.

```json
{
  "agentId": "my-agent-001",
  "total_invested": 100.0,
  "total_current_value": 115.5,
  "total_pnl_usd": 15.5,
  "total_pnl_pct": 15.5,
  "open_positions": 3,
  "total_trades": 7
}
```

#### `PATCH /agents/{agent_id}/flags`

toggle auto-invest flags. can be called from the dashboard or via agent chat.

| flag | description |
|------|-------------|
| `auto_rebalance` | deploy idle usdc into giza protocol (up to 15% apy). auto-withdraws when collateral needed. |
| `auto_freemonies` | poll metengine opportunities each cycle and auto-execute safe high-conviction trades (2-6% yield). checks solana usdc capacity before executing. |

```bash
# enable auto_freemonies
curl -X PATCH "$EIGENPOLY_API_URL/agents/my-agent-001/flags" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -d '{"auto_freemonies": true}'

# enable auto_rebalance
curl -X PATCH "$EIGENPOLY_API_URL/agents/my-agent-001/flags" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -d '{"auto_rebalance": true}'
```

response:
```json
{"agentId": "my-agent-001", "auto_rebalance": true, "auto_freemonies": false}
```

---

### markets

#### `GET /markets/trending?limit=20`

trending polymarket markets by 24h volume.

#### `GET /markets/search?q={query}&limit=20`

keyword search.

#### `GET /markets/{market_id}`

full market details: `question`, `yes_price`, `no_price`, `volume`, `volume_24h`, `liquidity`, `end_date`, `active`, `resolved`, `outcome`.

#### `GET /markets/analysis?limit=10`

market analysis with per-market `liquidity_score` (HIGH/MEDIUM/LOW), `opportunity_signal` (STRONG/MODERATE/VOLUME_SPIKE/NEUTRAL), and `spread`.

---

### metengine — smart money analytics (x402 solana pay-per-use)

every paid endpoint automatically charges your solana vault usdc via x402. check capacity first.

**how x402 works:**
1. request hits endpoint
2. backend receives `402 payment required` with amount + solana recipient
3. backend derives your solana vault key from tee mnemonic, broadcasts usdc transfer
4. retries with `X-PAYMENT` header
5. metengine validates and returns data

**always check capacity before paid calls:**
```bash
curl "$EIGENPOLY_API_URL/metengine/capacity" \
  -H "x-api-key: $EIGENPOLY_API_KEY"
```

response:
```json
{
  "solana_address": "8B9aLD...",
  "sol_balance": 0.05,
  "usdc_balance": 2.5,
  "calls_available": {"trending": 25, "intelligence": 10},
  "min_calls_across_endpoints": 10,
  "low_balance_warning": false,
  "recommendation": "balance sufficient for ~10 paid calls"
}
```

if `low_balance_warning` is true, fund the solana vault before proceeding:
- address: the `solana_address` from the response
- send usdc on solana mainnet (mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)

#### `GET /metengine/health` (free)
#### `GET /metengine/pricing` (free — shows per-endpoint cost)

#### `GET /metengine/trending?timeframe=24h&sort_by=volume_spike&limit=20`

markets with volume spikes and smart money inflow.

#### `GET /metengine/opportunities?min_signal_strength=&min_smart_wallets=`

smart money opportunity scanner. use this for `auto_freemonies` signal source.

#### `GET /metengine/high-conviction?min_smart_wallets=5&min_avg_score=65`

markets where multiple smart wallets agree.

#### `GET /metengine/intelligence/{condition_id}?top_n_wallets=10`

deep smart money analysis for a single market.

#### `GET /metengine/trades/{condition_id}?timeframe=24h&smart_money_only=false`

recent trades for a market.

#### `GET /metengine/whale-trades?min_usdc=10000&timeframe=24h`

whale trades ($10k+ by default) across all markets.

#### `GET /metengine/wallet/{address}`

wallet score, stats, and open positions.

#### `GET /metengine/wallet/{address}/pnl?timeframe=90d`

pnl breakdown by position.

#### `GET /metengine/top-performers?timeframe=7d&metric=pnl&limit=25`

top performing wallet leaderboard.

#### `GET /metengine/alpha-callers?days_back=30&min_days_early=7&min_bet_usdc=100`

wallets that called outcomes 7+ days before resolution.

---

### vaults — base defi usdc yields

#### `GET /vaults/base?min_tvl=1000000&min_apy=0`

current usdc vault apys on base: fluid, aave v3, compound v3, euler, morpho. sorted by apy descending.

```bash
curl "$EIGENPOLY_API_URL/vaults/base"
```

response:
```json
{
  "chain": "base",
  "best_apy": 7.2,
  "best_protocol": "Fluid",
  "total_checked": 5,
  "vaults": [
    {
      "protocol": "Fluid",
      "protocol_slug": "fluid",
      "symbol": "USDC",
      "chain": "base",
      "apy": 7.2,
      "apy_base": 5.1,
      "apy_reward": 2.1,
      "tvl_usd": 45000000,
      "il_risk": "none"
    }
  ]
}
```

use this alongside `auto_rebalance` to understand where idle usdc is being deployed.

---

### analytics (sozu proxy)

#### `GET /analytics/opportunities`
#### `GET /analytics/opportunities/{id}`
#### `POST /analytics/opportunities/{id}/acknowledge`
#### `GET /analytics/wallets`
#### `GET /analytics/wallets/{address}/analyze`

---

### deposit

> **CRITICAL RULE — never guess or construct deposit addresses.**
> deposit addresses are generated server-side by the polymarket bridge api.
> you MUST call `POST /deposit/address` every time a user asks for a deposit address.
> never reuse a previous address, never derive one from the wallet address, never make one up.
> if the api call fails, tell the user it failed — do not fall back to any address.

#### `GET /deposit/supported-assets`

lists all chains and tokens accepted by the polymarket bridge with per-token minimum amounts.
call this first if the user asks what they can send or what the minimum is.

```bash
curl "https://api.eigenpoly.xyz/deposit/supported-assets"
```

key minimums (as of last check): Base USDC min $2, Ethereum min $7.

#### `POST /deposit/address` — always call this, never skip it

**required every time.** returns a fresh bridge deposit address for the agent's safe wallet.
the address is generated by `bridge.polymarket.com` and is unique per safe wallet.

```bash
curl -X POST "https://api.eigenpoly.xyz/deposit/address" \
  -H "x-api-key: $EIGENPOLY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agentId": "my-agent-001"}'
```

response:
```json
{
  "agentId": "my-agent-001",
  "eoaAddress": "0x...",
  "safeAddress": "0x...",
  "depositAddresses": {
    "evm": "0x612f5A9bE1f9e57Ad94C5c4000b45b9AcE00433f",
    "svm": "43EnkSCwJ7hYqDvhKTesngVzoFj2d3C58STjdoV5pfHv",
    "tron": "TXiBArkPUXHViV5iYpwzzb2sj9oKSAiyxd",
    "btc": "bc1q..."
  },
  "note": "Funds will be bridged to USDC.e on your Polymarket Safe wallet."
}
```

tell the user:
- for Base/Ethereum/Arbitrum/any EVM chain → send to `depositAddresses.evm`
- for Solana → send to `depositAddresses.svm`
- funds land in their **safe wallet** (`safeAddress`), not the EOA
- do NOT send to the EOA address or the safe address directly — only to the deposit address

#### `POST /deposit/quote`

get a bridge quote before sending.

```bash
curl -X POST "https://api.eigenpoly.xyz/deposit/quote" \
  -H "Content-Type: application/json" \
  -d '{"fromAmountBaseUnit": "2200000", "fromChainId": "8453", "fromTokenAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}'
```

`fromAmountBaseUnit` is in token base units (USDC has 6 decimals, so 2.2 USDC = `"2200000"`).
chain ids: Base=8453, Ethereum=1, Arbitrum=42161, Polygon=137.

#### `GET /deposit/info`

quick funding reference — methods, addresses, important notes about USDC.e vs native USDC.

---

### misc

#### `GET /stats` (public)

platform stats: total agents, trades, volume, open positions.

#### `GET /health` (public)

`{"ok": true}`

---

## agent trading flow

1. **register** — `POST /register` — get api key + polygon eoa + solana vault
2. **fund** — send usdc.e to polygon eoa for trading, usdc to solana vault for metengine
3. **check capacity** — `GET /metengine/capacity` — confirm solana usdc before paid calls
4. **find markets** — `GET /markets/search?q=...` or `GET /metengine/opportunities`
5. **analyze** — `GET /markets/analysis` or `GET /metengine/intelligence/{id}`
6. **trade** — `POST /trade` with marketId + side + amount
7. **monitor** — `GET /agents/{id}/positions` for live p&l
8. **auto-invest** — `PATCH /agents/{id}/flags` to enable `auto_rebalance` or `auto_freemonies`
9. **vault yields** — `GET /vaults/base` to see where auto_rebalance is parking usdc

## route summary

| route | method | auth | description |
|-------|--------|------|-------------|
| `/register` | POST | none | register agent, get api key + evm + solana wallets |
| `/balance/{id}` | GET | x-api-key | multi-chain: polygon eoa+safe, solana vault, base eoa |
| `/trade` | POST | x-api-key | place bet on polymarket |
| `/agents/{id}/positions` | GET | x-api-key | positions with live p&l |
| `/agents/{id}/trades` | GET | x-api-key | trade history |
| `/agents/{id}/pnl` | GET | x-api-key | p&l summary |
| `/agents/{id}/flags` | PATCH | x-api-key | toggle auto_rebalance / auto_freemonies |
| `/markets/trending` | GET | none | trending markets |
| `/markets/search` | GET | none | search markets |
| `/markets/{id}` | GET | none | market details |
| `/markets/analysis` | GET | x-api-key | market signals |
| `/metengine/capacity` | GET | x-api-key | solana usdc balance + call capacity |
| `/metengine/trending` | GET | x-api-key + x402 | smart money trending markets |
| `/metengine/opportunities` | GET | x-api-key + x402 | opportunity scanner |
| `/metengine/high-conviction` | GET | x-api-key + x402 | high conviction markets |
| `/metengine/intelligence/{id}` | GET | x-api-key + x402 | deep market intelligence |
| `/metengine/trades/{id}` | GET | x-api-key + x402 | market trades |
| `/metengine/whale-trades` | GET | x-api-key + x402 | whale trades |
| `/metengine/wallet/{addr}` | GET | x-api-key + x402 | wallet profile |
| `/metengine/top-performers` | GET | x-api-key + x402 | top wallets leaderboard |
| `/metengine/alpha-callers` | GET | x-api-key + x402 | early callers |
| `/vaults/base` | GET | none | base defi usdc vault apys |
| `/analytics/opportunities` | GET | session | sozu opportunities |
| `/analytics/wallets/{addr}/analyze` | GET | session | wallet analytics |
| `/deposit/supported-assets` | GET | none | supported deposit chains |
| `/stats` | GET | none | platform stats |
| `/health` | GET | none | health check |

## security

- wallet keys are tee-derived from mnemonic injected by eigencompute kms — never written to disk
- api keys are sha-256 hashed before db storage — raw key shown only at registration
- `auto_rebalance` and `auto_freemonies` flags can only be toggled by the agent api key holder or the dashboard owner — not publicly settable
- solana private key is derived in-memory for x402 payments and never stored or logged
