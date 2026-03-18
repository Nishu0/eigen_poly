"""Key export route — allows authenticated agents to export their private key.

This enables agents to import their wallet into MetaMask or other wallets
to directly manage funds that were sent to their EOA.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.tee_wallet import derive_wallet, is_tee_mode
from routes.oauth import get_current_user
from lib.database import get_pool


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


class ExportSolanaKeyResponse(BaseModel):
    agentId: str
    solanaAddress: str
    privateKeyB58: str
    walletMode: str
    warning: str


async def _resolve_agent(req_agent_id: str, request: Request, api_key: Optional[str]):
    """Resolve agent from API key or session cookie, verify ownership."""
    if api_key and api_key.startswith("epk_"):
        key_hash = hash_api_key(api_key)
        agent = await store.get_agent_by_key_hash(key_hash)
        if not agent or agent.agent_id != req_agent_id:
            raise HTTPException(status_code=403, detail="API key does not match agent")
        return agent

    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Missing API key or valid session")

    agent = await store.get_agent(req_agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    pool = get_pool()
    owner = await pool.fetchval("SELECT owner_id FROM agents WHERE agent_id = $1", req_agent_id)
    if owner != user["sub"]:
        raise HTTPException(status_code=403, detail="You do not own this agent")

    return agent


@router.post("/export-key", response_model=ExportKeyResponse)
async def export_private_key(
    req: ExportKeyRequest,
    request: Request,
    api_key: Optional[str] = Header(default=None, alias="x-api-key"),
):
    """Export the EVM private key for MetaMask import.

    Requires API key ownership or session cookie with agent ownership.
    """
    agent = await _resolve_agent(req.agentId, request, api_key)

    if not is_tee_mode():
        raise HTTPException(
            status_code=503,
            detail="Key export only available in TEE mode. In local dev, use POLYCLAW_PRIVATE_KEY from .env",
        )

    wallet = derive_wallet(agent.wallet_index)
    return ExportKeyResponse(
        agentId=agent.agent_id,
        walletAddress=wallet.address,
        privateKey=wallet.private_key,
        walletMode="tee",
        warning="This is your TEE-derived EVM private key. Anyone with this key can drain your wallet. Store it securely and never share it.",
    )


@router.post("/export-solana-key", response_model=ExportSolanaKeyResponse)
async def export_solana_key(
    req: ExportKeyRequest,
    request: Request,
    api_key: Optional[str] = Header(default=None, alias="x-api-key"),
):
    """Export the Solana vault private key (base58) for Phantom or Solflare import.

    Requires API key ownership or session cookie with agent ownership.
    """
    from lib.tee_wallet import derive_solana_wallet

    agent = await _resolve_agent(req.agentId, request, api_key)

    if not is_tee_mode():
        raise HTTPException(
            status_code=503,
            detail="Key export only available in TEE mode.",
        )

    sol = derive_solana_wallet(agent.wallet_index)
    return ExportSolanaKeyResponse(
        agentId=agent.agent_id,
        solanaAddress=sol.address,
        privateKeyB58=sol.private_key_b58,
        walletMode="tee",
        warning="This is your TEE-derived Solana private key (base58). Import into Phantom or Solflare. Anyone with this key can drain your Solana vault.",
    )
