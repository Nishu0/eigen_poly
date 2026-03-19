"""Agent store — PostgreSQL-backed registration storage."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from lib.database import get_pool


@dataclass
class Agent:
    """Registered agent record."""

    agent_id: str
    wallet_address: str
    api_key_hash: str
    wallet_index: int
    polygon_safe: str
    solana_wallet: str
    scopes: list[str]
    created_at: str
    auto_rebalance: bool = False
    auto_freemonies: bool = False
    freemonies_max_markets: int = 2
    freemonies_amount_per_market: float = 2.0


class AgentStore:
    """PostgreSQL-backed agent store."""

    async def get_next_wallet_index(self) -> int:
        """Get the next available wallet derivation index."""
        pool = get_pool()
        max_index = await pool.fetchval("SELECT COALESCE(MAX(wallet_index), -1) FROM agents")
        return max_index + 1

    async def register(
        self,
        agent_id: str,
        wallet_address: str,
        api_key_hash: str,
        wallet_index: int = 0,
        polygon_safe: str = "",
        solana_wallet: str = "",
    ) -> Agent:
        """Register a new agent. Raises ValueError if already exists."""
        pool = get_pool()
        scopes = ["trade", "balance", "markets"]
        now = datetime.now(timezone.utc)

        try:
            await pool.execute(
                """
                INSERT INTO agents (agent_id, wallet_address, api_key_hash, wallet_index, polygon_safe, solana_wallet, scopes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                agent_id,
                wallet_address.lower(),
                api_key_hash,
                wallet_index,
                polygon_safe,
                solana_wallet,
                scopes,
                now,
            )
        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                raise ValueError(f"Agent already registered: {agent_id}")
            raise

        return Agent(
            agent_id=agent_id,
            wallet_address=wallet_address.lower(),
            api_key_hash=api_key_hash,
            wallet_index=wallet_index,
            polygon_safe=polygon_safe,
            solana_wallet=solana_wallet,
            scopes=scopes,
            created_at=now.isoformat(),
        )

    async def update_flags(
        self,
        agent_id: str,
        auto_rebalance: Optional[bool] = None,
        auto_freemonies: Optional[bool] = None,
        freemonies_max_markets: Optional[int] = None,
        freemonies_amount_per_market: Optional[float] = None,
    ) -> None:
        """Toggle flags and update freemonies config for an agent."""
        pool = get_pool()
        if auto_rebalance is not None:
            await pool.execute(
                "UPDATE agents SET auto_rebalance = $1 WHERE agent_id = $2",
                auto_rebalance, agent_id,
            )
        if auto_freemonies is not None:
            await pool.execute(
                "UPDATE agents SET auto_freemonies = $1 WHERE agent_id = $2",
                auto_freemonies, agent_id,
            )
        if freemonies_max_markets is not None:
            await pool.execute(
                "UPDATE agents SET freemonies_max_markets = $1 WHERE agent_id = $2",
                freemonies_max_markets, agent_id,
            )
        if freemonies_amount_per_market is not None:
            await pool.execute(
                "UPDATE agents SET freemonies_amount_per_market = $1 WHERE agent_id = $2",
                freemonies_amount_per_market, agent_id,
            )

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Lookup agent by ID."""
        pool = get_pool()
        row = await pool.fetchrow("SELECT * FROM agents WHERE agent_id = $1", agent_id)
        return self._row_to_agent(row) if row else None

    async def get_agent_by_key_hash(self, api_key_hash: str) -> Optional[Agent]:
        """Lookup agent by hashed API key."""
        pool = get_pool()
        row = await pool.fetchrow("SELECT * FROM agents WHERE api_key_hash = $1", api_key_hash)
        return self._row_to_agent(row) if row else None

    async def list_agents(self) -> list[Agent]:
        """Return all registered agents."""
        pool = get_pool()
        rows = await pool.fetch("SELECT * FROM agents ORDER BY created_at DESC")
        return [self._row_to_agent(r) for r in rows]

    def _row_to_agent(self, row) -> Agent:
        """Convert asyncpg Row to Agent dataclass."""
        return Agent(
            agent_id=row["agent_id"],
            wallet_address=row["wallet_address"],
            api_key_hash=row["api_key_hash"],
            wallet_index=row.get("wallet_index", 0) or 0,
            polygon_safe=row.get("polygon_safe") or "",
            solana_wallet=row.get("solana_wallet") or "",
            scopes=list(row["scopes"]) if row["scopes"] else [],
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
            auto_rebalance=bool(row.get("auto_rebalance", False)),
            auto_freemonies=bool(row.get("auto_freemonies", False)),
            freemonies_max_markets=int(row.get("freemonies_max_markets") or 2),
            freemonies_amount_per_market=float(row.get("freemonies_amount_per_market") or 2.0),
        )
