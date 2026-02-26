"""Balance route — fetch aggregate per-chain balances for an agent."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.auth import require_api_key, hash_api_key
from lib.agent_store import AgentStore
from lib.wallet_manager import WalletManager


router = APIRouter()
store = AgentStore()


class PolygonBalance(BaseModel):
    pol: float
    usdc_e: float


class SolanaBalance(BaseModel):
    sol: float
    vault_balance_usd: float


class BalanceResponse(BaseModel):
    agentId: str
    polygon: PolygonBalance
    solana: SolanaBalance
    total_usd: float


@router.get("/balance/{agent_id}", response_model=BalanceResponse)
async def get_balance(agent_id: str, api_key: str = Depends(require_api_key)):
    """Fetch aggregate balances for a registered agent."""

    # Verify API key ownership
    key_hash = hash_api_key(api_key)
    agent = await store.get_agent_by_key_hash(key_hash)
    if not agent or agent.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="API key does not match agent")

    # Fetch Polygon balances via WalletManager
    try:
        wallet = WalletManager()
        if wallet.is_unlocked:
            balances = wallet.get_balances()
            polygon = PolygonBalance(pol=balances.pol, usdc_e=balances.usdc_e)
        else:
            polygon = PolygonBalance(pol=0.0, usdc_e=0.0)
    except Exception:
        polygon = PolygonBalance(pol=0.0, usdc_e=0.0)

    # Solana vault balances — placeholder for MVP
    solana = SolanaBalance(sol=0.0, vault_balance_usd=0.0)

    # Approximate total USD (USDC.e ≈ 1 USD)
    total_usd = polygon.usdc_e + solana.vault_balance_usd

    return BalanceResponse(
        agentId=agent_id,
        polygon=polygon,
        solana=solana,
        total_usd=total_usd,
    )
