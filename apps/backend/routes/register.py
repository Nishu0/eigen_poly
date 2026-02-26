"""Register route — simplified agent onboarding.

Agents only provide a name. The server derives a wallet from the
TEE mnemonic using HD derivation. No key material is stored in the DB.
"""

from eth_account import Account

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib.auth import generate_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_address, is_tee_mode


router = APIRouter()
store = AgentStore()


class RegisterRequest(BaseModel):
    agentId: str


class RegisterResponse(BaseModel):
    status: str
    agentId: str
    apiKey: str
    walletAddress: str
    walletMode: str
    credentialStore: str


@router.post("/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest):
    """Register an agent — just provide a name.

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
        walletMode=wallet_mode,
        credentialStore="~/.eigenpoly/credentials.json",
    )
