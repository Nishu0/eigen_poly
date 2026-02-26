"""Agent store — PostgreSQL-backed registration storage."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from lib.database import get_pool


@dataclass
class Agent:
    """Registered agent record."""

    agent_id: str
    wallet_address: str
    api_key_hash: str
    polygon_safe: str
    solana_vault: str
    scopes: list[str]
    created_at: str


class AgentStore:
    """PostgreSQL-backed agent store."""

    async def register(
        self,
        agent_id: str,
        wallet_address: str,
        api_key_hash: str,
        polygon_safe: str = "",
        solana_vault: str = "",
    ) -> Agent:
        """Register a new agent. Raises ValueError if already exists."""
        pool = get_pool()
        scopes = ["trade", "balance", "markets"]
        now = datetime.now(timezone.utc)

        try:
            await pool.execute(
                """
                INSERT INTO agents (agent_id, wallet_address, api_key_hash, polygon_safe, solana_vault, scopes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                agent_id,
                wallet_address.lower(),
                api_key_hash,
                polygon_safe,
                solana_vault,
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
            polygon_safe=polygon_safe,
            solana_vault=solana_vault,
            scopes=scopes,
            created_at=now.isoformat(),
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
            polygon_safe=row["polygon_safe"] or "",
            solana_vault=row["solana_vault"] or "",
            scopes=list(row["scopes"]) if row["scopes"] else [],
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
        )
