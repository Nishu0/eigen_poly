# Experimental Features

> These features are live in production but still evolving. APIs, defaults, and behavior may change. Use with small amounts until you're comfortable.

---

## 1. Auto-Rebalance — Idle USDC Yield Optimizer

Automatically moves your agent's idle Base USDC into the highest-yielding DeFi protocol every 3 hours. No manual intervention required.

### How it works

1. Checks your agent's USDC balance on Base
2. Fetches live APY data from DefiLlama for Morpho, Fluid, Euler, Aave v3, and Compound v3 (Base)
3. If idle USDC exceeds `REBALANCE_MIN_USDC` (default $10), deposits into the best vault
4. If a better vault appears with APY improvement > `REBALANCE_APY_THRESHOLD` (default 0.5%), rebalances to it
5. All actions are logged to the `vault_logs` DB table

### Supported protocols

| Protocol | Interface | Pool source |
|----------|-----------|-------------|
| Morpho | ERC4626 | DefiLlama (dynamic) |
| Fluid | ERC4626 | DefiLlama (dynamic) |
| Euler | ERC4626 | DefiLlama (dynamic) |
| Aave v3 | Pool.supply / withdraw | Env var |
| Compound v3 | Comet.supply / withdraw | Env var |

### Enable it

```bash
PATCH /agents/{agent_id}/flags
{ "auto_rebalance": true }
```

### Configuration (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| `REBALANCE_MIN_USDC` | `10` | Min idle USDC to trigger a deposit |
| `REBALANCE_APY_THRESHOLD` | `0.5` | Min APY improvement (%) to trigger a rebalance |
| `REBALANCE_INTERVAL_HOURS` | `3` | Cron interval in hours |
| `REBALANCE_MIN_TVL` | `1000000` | Min vault TVL to consider (safety filter) |
| `BASE_USDC_ADDRESS` | mainnet USDC | Override USDC contract on Base |
| `AAVE_V3_POOL_BASE` | canonical | Aave v3 Pool contract |
| `AAVE_V3_AUSDC_BASE` | canonical | Aave v3 aUSDC contract |
| `COMPOUND_V3_COMET_BASE` | canonical | Compound v3 Comet contract |

### API endpoints

```
GET  /rebalance/{agent_id}/position   — live on-chain position value + earnings
GET  /rebalance/{agent_id}/logs       — full action history
GET  /rebalance/{agent_id}/summary    — dashboard card (invested, current, APY, gain)
POST /rebalance/{agent_id}/trigger    — manually trigger a rebalance cycle (for testing)
```

### Dashboard prompt examples

> "Show me my rebalance position and earnings"

> "What's the current APY on my yield position?"

> "Trigger a manual rebalance and show the result"

---

## 2. Auto-Freemonies — Smart Money Market Trading

Automatically invests in high-conviction Polymarket markets sourced from MetEngine smart wallet analytics. Runs every 3 hours (offset from rebalance cron).

**Requires Solana USDC** — MetEngine calls are x402 micropayment-gated on Solana.

### How it works

1. Checks your agent's Solana USDC balance (required to pay MetEngine x402 fees)
2. Calls MetEngine `/markets/opportunities` for HIGH-signal markets
3. Filters out markets where you already have an open position
4. Picks the top N markets (configurable, default 2)
5. Executes a buy trade per market using your Polygon Safe wallet
6. Records each trade and position in the DB

### Enable it

```bash
PATCH /agents/{agent_id}/flags
{
  "auto_freemonies": true,
  "freemonies_max_markets": 2,
  "freemonies_amount_per_market": 2.0
}
```

### Configuration

| Field | Default | Min | Description |
|-------|---------|-----|-------------|
| `freemonies_max_markets` | `2` | 1 | Markets to invest in per cycle |
| `freemonies_amount_per_market` | `2.0` | 2.0 | USDC per trade |

Both fields are per-agent in the DB and configurable from the dashboard.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FREEMONIES_INTERVAL_HOURS` | same as `REBALANCE_INTERVAL_HOURS` | Override cron interval |
| `METENGINE_BASE` | `https://agent.metengine.xyz` | MetEngine base URL |
| `SOLANA_RPC_URL` | mainnet-beta | Solana RPC for balance checks |
| `METENGINE_SOLANA_KEY` | — | Solana private key (non-TEE mode only) |

### Requirements

- Agent must have a funded Solana wallet (for MetEngine x402 fees)
- Agent must have USDC.e on Polygon (for trade execution)
- MetEngine returns market signals — quality depends on smart wallet activity

---

## 3. TEE-Secured Wallet Derivation

Agent wallets are derived inside an Intel TDX Trusted Execution Environment (TEE) via EigenCompute. The MNEMONIC is injected via KMS and never leaves the enclave.

- **EVM wallets**: derived at `m/44'/60'/0'/0/{index}`
- **Solana wallets**: derived at `m/44'/501'/0'/0/{index}'`
- Each registered agent gets a unique `wallet_index` — wallets are deterministic and recoverable from the same seed

In non-TEE mode (local dev), set `MNEMONIC` or `METENGINE_SOLANA_KEY` directly.

---

## 4. Cross-Chain Deposit Routing

The deposit route accepts either an `agentId` or a raw `safeAddress` and returns typed deposit addresses with chain annotations:

```bash
POST /deposit/address
{ "safeAddress": "0xD01C..." }
```

Returns EVM (Ethereum/Base/Arbitrum), SVM (Solana), BTC, and TVM (Tron) deposit addresses — each annotated with supported chains. Funds sent to the EVM address on Base are bridged to your Polygon Safe automatically via the Polymarket Bridge.

---

## Coming Soon

- **Auto-close positions** — Automatically close positions when a market resolves or P&L target is hit
- **Multi-agent portfolio view** — Cross-agent P&L dashboard with aggregate stats
- **Freemonies exit strategy** — Auto-sell when positions reach configurable profit targets
- **Rebalance to Solana** — Auto-fund Solana wallet from Base USDC for MetEngine x402 fees
- **Risk controls** — Per-agent max drawdown, daily loss limit, position size caps
- **MetEngine signal scoring** — Weight trade size by signal strength / smart wallet count
- **Vault strategy selection** — Per-agent preferred protocol whitelist / blacklist
- **Push notifications** — Webhook or Telegram alerts for trades, rebalances, and position changes
