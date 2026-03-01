"""Agent registration — register, get API key + TEE wallet + claim URL.

Derives wallet from TEE mnemonic (or creates one for local dev).
Computes Polymarket proxy/Safe wallet address on-chain.
Creates a device code for human to claim via Google OAuth.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from web3 import Web3
from eth_account import Account

from lib.auth import generate_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_address, is_tee_mode
from lib.contracts import CONTRACTS, PROXY_WALLET_ABI
from routes.device import create_device_code


router = APIRouter()
store = AgentStore()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


class RegisterRequest(BaseModel):
    agentId: str
    agentFirst: bool = True  # Agent gets API key immediately (recommended)


class RegisterResponse(BaseModel):
    status: str
    agentId: str
    apiKey: str
    walletAddress: str
    safeWalletAddress: str
    walletType: str
    walletMode: str
    claimCode: str
    claimUrl: str
    deviceCode: str
    expiresIn: int
    fundingInfo: dict
    nextSteps: list[str]


def _get_safe_address(eoa_address: str) -> str:
    """Compute Polymarket proxy/Safe wallet address for an EOA."""
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
    """Register an agent — get API key + wallet + claim URL.

    Agent-first mode: API key returned immediately, human claims later
    via the claim URL with Google OAuth.
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
        account = Account.create()
        wallet_address = account.address
        wallet_mode = "local"

    # Compute Polymarket Safe proxy wallet
    safe_address = _get_safe_address(wallet_address)

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    # Register agent
    agent = await store.register(
        agent_id=req.agentId,
        wallet_address=wallet_address,
        api_key_hash=key_hash,
        wallet_index=wallet_index,
    )

    # Create device code for human claim
    device = await create_device_code(req.agentId)
    claim_url = f"{FRONTEND_URL}/device?code={device['userCode']}"

    return RegisterResponse(
        status="registered",
        agentId=agent.agent_id,
        apiKey=api_key,
        walletAddress=wallet_address,
        safeWalletAddress=safe_address,
        walletType="EOA + Safe",
        walletMode=wallet_mode,
        claimCode=device["userCode"],
        claimUrl=claim_url,
        deviceCode=device["deviceCode"],
        expiresIn=device["expiresIn"],
        fundingInfo={
            "polygon_usdc_e": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "warning": "Send USDC.e (bridged USDC) on Polygon to the EOA address",
            "send_to": wallet_address,
            "safe_wallet": safe_address,
            "note": "CLOB trading uses EOA balance. Send funds to EOA, not Safe.",
            "deposit_supported_assets": "GET /deposit/supported-assets",
            "deposit_address": "POST /deposit/address",
            "min_deposit_usd": 1,
        },
        nextSteps=[
            "1. Store your apiKey — it is shown only once",
            f"2. Send the claim URL to the human owner: {claim_url}",
            "3. Human opens the URL → Google login → Authorize",
            "4. Fund wallet with USDC.e: GET /deposit/supported-assets",
            "5. Start trading: POST /trade",
        ],
    )
