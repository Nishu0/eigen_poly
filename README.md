# eigenpoly

polymarket alpha detection and trade execution platform running inside eigencompute tee nodes.

agents register, get a tee-derived wallet, then call endpoints to find opportunities and execute on-chain trades. smart money analytics are pay-per-use via x402 (solana usdc). market analysis proxies through sozu without exposing upstream urls.

---

## stack

- **backend** — python, fastapi, asyncpg
- **frontend** — next.js 15, react 19, typescript
- **database** — postgresql
- **chain** — polygon mainnet (trading), solana (x402 payments)
- **tee** — eigencompute (wallet derivation, policy enforcement)

---

## how it works

**agent registration**

`POST /register` derives an evm wallet from the tee-injected mnemonic using bip44 path `m/44'/60'/0'/0/{index}`. each agent gets a unique eoa and a deterministic safe proxy (create2). an api key (`epk_...`) is returned and sha256-hashed before storage. a solana vault is also derived from the same mnemonic for x402 payments.

**claiming an agent**

the registration response includes a device code and a claim url. the user opens the url, signs in with google oauth, and the agent links to their account. after linking, agents appear in the dashboard.

**trade execution**

`POST /trade` takes market id, side, and amount. the backend:
1. checks usdc balance and approvals on the agent safe
2. calls polymarket ctf exchange to split usdc into yes+no tokens
3. sells the unwanted token via clob (fok order, 5% slippage cap, proxy rotation for cloudflare bypass)
4. records the trade and open position in postgresql

**position tracking**

`GET /agents/{id}/positions` reads positions from db and fetches live clob prices to compute unrealized pnl.

**sozu analytics**

`/analytics/*` proxies to a sozu upstream that runs polymarket wallet analytics. the upstream url is hidden from clients. covers opportunities, wallet profiles, and wallet analysis.

**metengine (x402)**

`/metengine/*` wraps smart money analytics behind solana micropayments:
1. client makes request with api key
2. backend gets `402 payment required` from metengine with amount and solana recipient
3. backend derives solana wallet from tee mnemonic, broadcasts usdc transfer
4. retries request with `X-PAYMENT` header containing signed proof
5. metengine validates and returns data

**markets**

`/markets/*` hits the polymarket gamma api and returns structured data with spread, liquidity score, and opportunity signals.

---

## routes

### auth
| method | path | auth | description |
|--------|------|------|-------------|
| POST | `/register` | none | register agent, get api key + wallet |
| GET | `/device/{code}` | none | device code info |
| POST | `/device/authorize` | session | link agent to google account |
| POST | `/device/deny` | session | deny agent claim |
| POST | `/device/poll` | api key | poll authorization status |
| GET | `/oauth/google` | none | start google oauth |
| GET | `/oauth/google/callback` | none | oauth callback |
| GET | `/oauth/me` | session | current user |
| POST | `/oauth/logout` | session | clear session |

### trading
| method | path | auth | description |
|--------|------|------|-------------|
| POST | `/trade` | api key | execute on-chain trade |
| GET | `/agents/{id}/positions` | session | positions with live pnl |
| GET | `/agents/{id}/trades` | session | trade history |
| GET | `/agents/{id}/pnl` | session | pnl summary |
| PATCH | `/agents/{id}/flags` | api key | toggle auto_rebalance / auto_freemonies flags |
| GET | `/balance/{agent_id}` | api key | multi-chain balances: polygon eoa+safe, solana vault, base eoa |

### markets
| method | path | auth | description |
|--------|------|------|-------------|
| GET | `/markets/trending` | api key | trending by 24h volume |
| GET | `/markets/search` | api key | keyword search |
| GET | `/markets/analysis` | api key | volume, liquidity, signals |
| GET | `/markets/{id}` | api key | single market detail |

### metengine (x402 solana pay-per-use)
| method | path | description |
|--------|------|-------------|
| GET | `/metengine/health` | health check (free) |
| GET | `/metengine/pricing` | pricing tiers (free) |
| GET | `/metengine/capacity` | solana usdc balance + how many paid calls you can afford |
| GET | `/metengine/trending` | markets with volume spikes and smart money activity |
| GET | `/metengine/opportunities` | smart money opportunity scanner |
| GET | `/metengine/high-conviction` | markets with highest smart money consensus |
| GET | `/metengine/intelligence/{condition_id}` | deep smart money data for one market |
| GET | `/metengine/trades/{condition_id}` | recent trades, filterable by smart money |
| GET | `/metengine/whale-trades` | whale trades ($10k+ minimum) across all markets |
| GET | `/metengine/wallet/{address}` | wallet score, stats, open positions |
| GET | `/metengine/wallet/{address}/pnl` | pnl by position |
| GET | `/metengine/top-performers` | top performing wallet leaderboard |
| GET | `/metengine/alpha-callers` | wallets that called outcomes 7+ days early |

### vaults
| method | path | auth | description |
|--------|------|------|-------------|
| GET | `/vaults/base` | none | usdc vault apys on base: fluid, aave v3, compound v3, euler, morpho |

### sozu analytics
| method | path | auth | description |
|--------|------|------|-------------|
| GET | `/analytics/opportunities` | session | trading opportunities |
| GET | `/analytics/opportunities/{id}` | session | single opportunity |
| POST | `/analytics/opportunities/{id}/acknowledge` | session | dismiss opportunity |
| GET | `/analytics/wallets` | session | top wallets |
| GET | `/analytics/wallets/{address}/analyze` | session | deep wallet analytics |

### deposit
| method | path | description |
|--------|------|-------------|
| GET | `/deposit/supported-assets` | supported chains and tokens |
| POST | `/deposit/address` | create cross-chain deposit address |
| POST | `/deposit/quote` | bridge quote |
| GET | `/deposit/info` | funding quick reference |

### misc
| method | path | auth | description |
|--------|------|------|-------------|
| GET | `/user/agents` | session | list owned agents |
| GET | `/user/logs` | session | api request logs (paginated) |
| GET | `/user/trades` | session | all trades across agents |
| POST | `/export-key` | session | export private key for metamask import |
| GET | `/stats` | none | platform stats (public) |
| GET | `/health` | none | service health |

---

## database

```
users          — google oauth accounts
agents         — api_key_hash, wallet_address, solana_vault, owner_id
device_codes   — pending oauth claims with expiry
trades         — split_tx, clob_order_id, status, error
positions      — entry data, token_id, clob_filled, status
agent_logs     — per-request logs: method, path, status, duration_ms
```

---

## wallet model

each agent gets three wallets derived from the tee mnemonic:

- **eoa** — evm signer at `m/44'/60'/0'/0/{index}`, receives bridge deposits
- **safe proxy** — polymarket trading account, deterministic create2 address from eoa
- **solana vault** — used only for x402 metengine payments

in production the mnemonic is injected by eigencompute kms and never leaves the enclave. local dev falls back to `POLYCLAW_PRIVATE_KEY`.

---

## environment variables

```
DATABASE_URL              postgresql://...
CHAINSTACK_NODE           polygon mainnet rpc
BASE_RPC_URL              base mainnet rpc (default: https://mainnet.base.org)
SOLANA_RPC_URL            solana mainnet rpc (default: https://api.mainnet-beta.solana.com)
OPENROUTER_API_KEY        llm api key
MNEMONIC                  injected by tee in production, do not set manually
POLYCLAW_PRIVATE_KEY      local dev fallback wallet
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
JWT_SECRET                random secret for session cookies
COOKIE_DOMAIN             .eigenpoly.xyz in prod, unset for local dev
FRONTEND_URL              http://localhost:3000
SOZU_BASE_URL             upstream sozu analytics url
METENGINE_SOLANA_KEY      local dev fallback for solana x402 payments
HTTPS_PROXY               optional socks5 proxy for clob requests
```

---

## local development

```bash
# install
bun install

# frontend (port 3000)
bun run dev --filter=web

# backend (port 8000)
cd apps/backend
uv sync
uv run uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

---

## deployment

| file | purpose |
|------|---------|
| `Dockerfile` | standard fastapi container |
| `Dockerfile.tee` | eigencompute tee build |
| `ecloud.yaml` | tee config (mnemonic injection, policy) |
| `Caddyfile` | tls termination and rate limiting |

---

## status

### working

- agent registration with tee-derived evm wallet + solana vault (both returned in registration response)
- multi-chain balance: polygon eoa+safe (pol + usdc.e), solana vault (sol + usdc), base eoa (eth + usdc) — with chain logos
- `/metengine/capacity` — checks solana usdc balance and calculates how many x402 calls you can afford
- `/vaults/base` — live usdc vault apys from defillama for fluid, aave v3, compound v3, euler, morpho on base
- `auto_rebalance` and `auto_freemonies` per-agent boolean flags stored in DB, togglable via `PATCH /agents/{id}/flags`
- google oauth device claim flow
- on-chain trade execution (usdc split + clob sell) on polygon
- position and trade storage with live pnl
- eoa and safe balance lookups
- cross-chain deposit address creation (ethereum, arbitrum, base, others)
- sozu analytics proxy (opportunities, wallet profiles)
- metengine x402 pay-per-use smart money analytics (all endpoints)
- trending, search, and analysis market endpoints via polymarket gamma
- api request logging per agent
- public platform stats endpoint
- frontend dashboard with positions and opportunity views
- device claim ui

### in progress

- **auto_rebalance flag** — per-agent boolean stored in DB. when enabled, idle usdc in the agent safe is automatically deployed into the highest-yield vault from `/vaults/base` (fluid, aave v3, compound v3, euler, morpho on base — typically 2-8% apy). the giza protocol is the primary target (up to 15% apy). withdrawals trigger automatically when the agent needs collateral. toggled via `PATCH /agents/{id}/flags` from the dashboard or via agent chat.

- **auto_freemonies flag** — per-agent boolean stored in DB. when enabled, the agent polls `/metengine/opportunities` each cycle, filters for high-conviction safe markets, and executes small trades (2-6% expected yield) using the configured investment amount. the agent checks `/metengine/capacity` first — if solana usdc is too low to pay for the calls, it surfaces a funding prompt instead of failing silently. toggled via `PATCH /agents/{id}/flags` from the dashboard or via agent chat.

### not done

- llm-based market relationship classification
- hedge pair computation and covering portfolio construction
- eigencompute policy enforcement before trade execution (ecloud.yaml wired but not enforced in route layer)
- automatic correlated pair discovery from market universe

---

## disclaimer

this project is for research and engineering purposes. prediction-market trading carries real financial risk. use conservative limits, isolate keys, and run only with capital you can afford to lose.
