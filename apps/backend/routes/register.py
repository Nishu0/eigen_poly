"""Agent registration — register, get API key + TEE wallet + claim URL."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from eth_account import Account

from lib.auth import generate_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_address, derive_solana_wallet, is_tee_mode
from lib.contracts import derive_polymarket_safe
from routes.device import create_device_code


router = APIRouter()
store = AgentStore()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


class RegisterRequest(BaseModel):
    agentId: str
    agentFirst: bool = True


class RegisterResponse(BaseModel):
    status: str
    agentId: str
    apiKey: str
    walletAddress: str
    safeWalletAddress: str
    solanaAddress: str
    walletType: str
    walletMode: str
    claimCode: str
    claimUrl: str
    deviceCode: str
    expiresIn: int
    fundingInfo: dict
    nextSteps: list[str]


def _get_safe_address(eoa_address: str) -> str:
    try:
        return derive_polymarket_safe(eoa_address)
    except Exception as e:
        print(f"Warning: could not derive Safe address: {e}")
        return ""


@router.post("/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest):
    """Register an agent — get API key + EVM wallet + Solana vault + claim URL."""

    existing = await store.get_agent(req.agentId)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{req.agentId}' already registered")

    wallet_index = await store.get_next_wallet_index()

    # derive EVM wallet
    if is_tee_mode():
        wallet_address = derive_address(wallet_index)
        wallet_mode = "tee"
    else:
        account = Account.create()
        wallet_address = account.address
        wallet_mode = "local"

    # derive Solana vault from same MNEMONIC
    solana_address = ""
    if is_tee_mode():
        try:
            sol = derive_solana_wallet(wallet_index)
            solana_address = sol.address
        except Exception as e:
            print(f"Warning: could not derive Solana wallet: {e}")

    safe_address = _get_safe_address(wallet_address)
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    agent = await store.register(
        agent_id=req.agentId,
        wallet_address=wallet_address,
        api_key_hash=key_hash,
        wallet_index=wallet_index,
        polygon_safe=safe_address,
        solana_vault=solana_address,
    )

    device = await create_device_code(req.agentId)
    claim_url = f"{FRONTEND_URL}/device?code={device['userCode']}"

    return RegisterResponse(
        status="registered",
        agentId=agent.agent_id,
        apiKey=api_key,
        walletAddress=wallet_address,
        safeWalletAddress=safe_address,
        solanaAddress=solana_address,
        walletType="EOA + Safe + Solana vault",
        walletMode=wallet_mode,
        claimCode=device["userCode"],
        claimUrl=claim_url,
        deviceCode=device["deviceCode"],
        expiresIn=device["expiresIn"],
        fundingInfo={
            "polygon_eoa": wallet_address,
            "polygon_safe": safe_address,
            "solana_vault": solana_address,
            "usdc_e_contract": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "solana_usdc_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "note": "fund eoa for polymarket trading (usdc.e on polygon). fund solana vault for metengine x402 calls (usdc on solana mainnet).",
            "deposit_supported_assets": "GET /deposit/supported-assets",
            "deposit_address": "POST /deposit/address",
        },
        nextSteps=[
            "1. store your apiKey — shown only once",
            f"2. share the claim url with the agent owner: {claim_url}",
            "3. owner opens url → google login → authorize",
            "4. fund polygon eoa with usdc.e for trading: GET /deposit/supported-assets",
            "5. fund solana vault with usdc for metengine x402 calls",
            "6. start trading: POST /trade",
        ],
    )
