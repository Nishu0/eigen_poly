# EigenCompute Integration — EigenPoly

> Verifiable, non-custodial agent wallets using Intel TDX Trusted Execution Environments.

## Why TEE?

With standard server encryption, whoever has the master key can decrypt all wallet private keys. **The operator must be trusted**, which is unacceptable for autonomous agents managing real funds.

EigenCompute solves this by running the backend inside an **Intel TDX TEE** (Trusted Execution Environment):

| | Standard Server | EigenCompute TEE |
|---|---|---|
| **Key storage** | Encrypted in DB, master key in env | Keys exist ONLY inside enclave |
| **Operator access** | Can decrypt with master key | Cannot extract keys |
| **Verification** | Trust the operator | Cryptographic attestation |
| **Key generation** | Server-side, operator can see | KMS → enclave only |

## Architecture

```
Agent                   EigenCompute TEE
  │                     ┌──────────────────────────┐
  │  POST /register     │  KMS → MNEMONIC env var  │
  │ ──────────────────► │  Derive wallet m/44'/60'  │
  │                     │  /0'/0/{agent_index}      │
  │ ◄────────────────── │  Return wallet address    │
  │  { apiKey, address} │                           │
  │                     │                           │
  │  POST /trade        │  Load agent's HD key      │
  │ ──────────────────► │  Sign on-chain tx         │
  │                     │  Submit to Polygon        │
  │ ◄────────────────── │  Return receipt           │
  │  { tradeId, tx }    │                           │
  │                     └──────────────────────────┘
  │                         ↑ Attestation proof
  │  GET /attestation       │ (anyone can verify
  │ ──────────────────►─────┘  the exact Docker image)
```

## How It Works

### 1. TEE Mnemonic

When you deploy to EigenCompute, a KMS (Key Management System) generates a **BIP-39 mnemonic phrase** and binds it to your app's enclave. This mnemonic:

- Is injected at runtime as `process.env.MNEMONIC` (or `os.environ["MNEMONIC"]` in Python)
- Is encrypted at rest in the KMS
- Is only decrypted and released to the verified Docker image inside the TEE
- Persists across deployments of the same app

### 2. Per-Agent Wallet Derivation

Each agent gets a unique wallet via HD derivation:

```
MNEMONIC (from TEE)
  └─ m/44'/60'/0'/0/0  → Agent #0 wallet
  └─ m/44'/60'/0'/0/1  → Agent #1 wallet
  └─ m/44'/60'/0'/0/2  → Agent #2 wallet
  ...
```

The DB only stores the **derivation index** (an integer), never any key material.

### 3. Transaction Signing

When an agent places a trade:
1. Backend reads `MNEMONIC` from TEE environment
2. Derives the agent's private key from their HD path
3. Signs the Polygon transaction inside the enclave
4. Submits to the blockchain
5. Private key is never written to disk or sent over the network

### 4. Attestation

Agents can verify the TEE is running the correct code:

```bash
curl https://your-app.eigencompute.xyz/attestation
```

Returns a cryptographic proof that:
- The exact Docker image hash matches the published source
- The TEE hardware is genuine Intel TDX
- The enclave has not been tampered with

## Local Development

For local dev (without a TEE), the wallet module falls back to a dev mnemonic:

```bash
# .env (local dev only — NOT used in production)
MNEMONIC="test test test test test test test test test test test junk"
```

**In production on EigenCompute**, the `MNEMONIC` env var is automatically provided by the KMS and is never visible to the operator.

## Deployment

### Prerequisites

```bash
# Install ecloud CLI
bunx @layr-labs/ecloud-cli --help

# Or install globally
bun add -g @layr-labs/ecloud-cli
```

### Step-by-step

```bash
# 1. Auth with EigenCloud
ecloud auth login
# Or generate a new key: ecloud auth generate --store

# 2. Docker login (for your registry)
docker login

# 3. Deploy the backend to TEE
cd apps/backend
ecloud compute app deploy
```

The CLI will:
- Build the Docker image from `Dockerfile.tee`
- Push to your registry
- Deploy to an Intel TDX TEE instance
- Return the app ID and instance IP
- The KMS automatically provisions the `MNEMONIC`

### EigenCompute Config

`ecloud.yaml`:
```yaml
name: eigenpoly-backend
version: "0.1.0"
runtime: docker
dockerfile: Dockerfile.tee
port: 8000
env:
  - DATABASE_URL        # Set in EigenCloud dashboard
  - CHAINSTACK_NODE     # Set in EigenCloud dashboard
  - MNEMONIC            # Auto-provided by TEE KMS
```

## File Map

| File | Purpose |
|------|---------|
| `lib/tee_wallet.py` | TEE wallet: read MNEMONIC, derive per-agent keys, sign txs |
| `lib/crypto.py` | Kept for backward compat, unused in TEE mode |
| `Dockerfile.tee` | Docker image for EigenCompute deployment |
| `ecloud.yaml` | EigenCompute app configuration |
| `eigen.md` | This documentation |

## Security Model

1. **Private keys never leave the TEE** — even the operator cannot extract them
2. **Attestation** — agents verify the enclave is running the published code
3. **KMS-bound mnemonic** — the mnemonic is tied to the specific app enclave
4. **HD derivation** — DB stores only an integer index, zero key material
5. **EigenLayer slashing** — operators stake ETH, tamper = slashed (future)
