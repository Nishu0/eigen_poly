"""Register route — agent onboarding with wallet signature verification."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib.auth import generate_api_key, verify_wallet_signature, hash_api_key
from lib.agent_store import AgentStore


router = APIRouter()
store = AgentStore()

SIGN_MESSAGE_TEMPLATE = "EigenPoly Agent Registration: {agent_id}"


class RegisterRequest(BaseModel):
    agentId: str
    walletAddress: str
    signature: str


class RegisterResponse(BaseModel):
    status: str
    agentId: str
    apiKey: str
    credentialStore: str
    accounts: dict


@router.post("/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest):
    """Register an agent, verify wallet ownership, issue API key."""

    # Check if already registered
    existing = store.get_agent(req.agentId)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{req.agentId}' already registered")

    # Verify wallet signature (EIP-191)
    message = SIGN_MESSAGE_TEMPLATE.format(agent_id=req.agentId)
    if not verify_wallet_signature(req.walletAddress, message, req.signature):
        raise HTTPException(status_code=401, detail="Invalid wallet signature")

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    # Register agent with production account placeholders
    # In production, these would create actual Polygon Safe + Solana vault
    polygon_safe = f"0x{req.walletAddress[2:6]}...safe"  # Placeholder
    solana_vault = "So1...vault"  # Placeholder

    agent = store.register(
        agent_id=req.agentId,
        wallet_address=req.walletAddress,
        api_key_hash=key_hash,
        polygon_safe=polygon_safe,
        solana_vault=solana_vault,
    )

    return RegisterResponse(
        status="registered",
        agentId=agent.agent_id,
        apiKey=api_key,  # Shown once — agent must store in credentials.json
        credentialStore="~/.eigenpoly/credentials.json",
        accounts={
            "polygonSafe": agent.polygon_safe,
            "solanaVault": agent.solana_vault,
        },
    )
