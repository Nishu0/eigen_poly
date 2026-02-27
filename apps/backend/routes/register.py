"""Agent registration — register, get API key + TEE wallet + Safe proxy.

Derives wallet from TEE mnemonic (or creates one for local dev).
Computes Polymarket proxy/Safe wallet address on-chain.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from web3 import Web3
from eth_account import Account

from lib.auth import generate_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_address, is_tee_mode
from lib.contracts import CONTRACTS, PROXY_WALLET_ABI


router = APIRouter()
store = AgentStore()


class RegisterRequest(BaseModel):
    agentId: str


class RegisterResponse(BaseModel):
    status: str
    agentId: str
    apiKey: str
    walletAddress: str
    safeWalletAddress: str
    walletType: str
    walletMode: str
    credentialStore: str
    fundingInfo: dict
    nextSteps: list[str]


def _get_safe_address(eoa_address: str) -> str:
    """Compute Polymarket proxy/Safe wallet address for an EOA.

    Calls getPolyProxyWalletAddress on the CTF Exchange contract.
    This is deterministic — same EOA always gets the same Safe.
    """
    rpc_url = os.environ.get("CHAINSTACK_NODE", "")
    if not rpc_url:
        return ""

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15, "proxies": {}}))
        exchange = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["CTF_EXCHANGE"]),
            abi=PROXY_WALLET_ABI,
        )
        safe_addr = exchange.functions.getPolyProxyWalletAddress(
            Web3.to_checksum_address(eoa_address)
        ).call()
        return safe_addr
    except Exception as e:
        print(f"Warning: could not derive Safe address: {e}")
        return ""


@router.post("/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest):
    """Register an agent — just provide a name.

    Returns both EOA wallet (signing key) and Polymarket Safe wallet (funds holder).
    In TEE mode: wallet derived from MNEMONIC via HD path (no key stored).
    In fallback mode: wallet generated via Account.create() (for local dev).
    """

    # Check if already registered
    existing = await store.get_agent(req.agentId)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{req.agentId}' already registered")

    # Get next wallet index
    wallet_index = await store.get_next_wallet_index()

    # Derive or generate wallet
    if is_tee_mode():
        wallet_address = derive_address(wallet_index)
        wallet_mode = "tee"
    else:
        # Fallback for local dev without MNEMONIC
        account = Account.create()
        wallet_address = account.address
        wallet_mode = "local"

    # Compute Polymarket Safe/proxy wallet address from EOA
    safe_address = _get_safe_address(wallet_address)

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    # Register — DB stores only the wallet_index (integer), never key material
    agent = await store.register(
        agent_id=req.agentId,
        wallet_address=wallet_address,
        api_key_hash=key_hash,
        wallet_index=wallet_index,
    )

    return RegisterResponse(
        status="registered",
        agentId=agent.agent_id,
        apiKey=api_key,  # Shown once — agent must store this
        walletAddress=wallet_address,
        safeWalletAddress=safe_address,
        walletType="EOA + Safe",
        walletMode=wallet_mode,
        credentialStore="~/.eigenpoly/credentials.json",
        fundingInfo={
            "polygon_usdc_e": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "warning": "Send USDC.e (bridged USDC) on Polygon, NOT native USDC",
            "send_to": safe_address or wallet_address,
            "deposit_supported_assets": "GET /deposit/supported-assets",
            "deposit_address": "POST /deposit/address",
            "min_deposit_usd": 45,
        },
        nextSteps=[
            "1. Store your apiKey — it is shown only once",
            "2. Check supported deposit assets: GET /deposit/supported-assets",
            f"3. Fund your Safe wallet ({safe_address or wallet_address}) with USDC.e on Polygon",
            "4. Or bridge from other chains: POST /deposit/address with your agentId",
            "5. Start trading: POST /trade",
        ],
    )
