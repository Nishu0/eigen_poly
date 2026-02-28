"""Key export route — allows authenticated agents to export their private key.

This enables agents to import their wallet into MetaMask or other wallets
to directly manage funds that were sent to their EOA.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_wallet, is_tee_mode


router = APIRouter()
store = AgentStore()


class ExportKeyRequest(BaseModel):
    agentId: str


class ExportKeyResponse(BaseModel):
    agentId: str
    walletAddress: str
    privateKey: str
    walletMode: str
    warning: str


@router.post("/export-key", response_model=ExportKeyResponse)
async def export_private_key(req: ExportKeyRequest, api_key: str = Depends(require_api_key)):
    """Export the agent's private key for importing into MetaMask or other wallets.

    ⚠️ This reveals the private key. Anyone with this key can control the wallet.
    Only use this to recover funds or import into another wallet.
    """

    # Verify API key ownership
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != req.agentId:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    # Derive the private key
    if is_tee_mode():
        wallet = derive_wallet(agent.wallet_index)
        return ExportKeyResponse(
            agentId=agent.agent_id,
            walletAddress=wallet.address,
            privateKey=wallet.private_key,
            walletMode="tee",
            warning="⚠️ This is your TEE-derived private key. Anyone with this key can control your wallet. Store it securely.",
        )
    else:
        raise HTTPException(
            status_code=503,
            detail="Key export only available in TEE mode. In local dev mode, use POLYCLAW_PRIVATE_KEY from .env",
        )
