"""Position storage — PostgreSQL-backed with trade recording."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from lib.database import get_pool


@dataclass
class PositionEntry:
    """Position entry stored in database."""

    position_id: str

    # Market info
    market_id: str
    question: str
    position: str  # YES or NO
    token_id: str

    # Entry data
    entry_time: str  # ISO timestamp
    entry_amount: float  # USD spent on split
    entry_price: float  # Price at time of purchase

    # Transaction records
    split_tx: str
    clob_order_id: Optional[str] = None
    clob_filled: bool = False

    # Status
    status: str = "open"  # open, closed, resolved
    notes: Optional[str] = None

    # Agent link
    agent_id: Optional[str] = None


class PositionStorage:
    """PostgreSQL-backed position storage."""

    async def add(self, entry: PositionEntry) -> None:
        """Add new position entry."""
        pool = get_pool()
        await pool.execute(
            """
            INSERT INTO positions (
                position_id, agent_id, market_id, question, position, token_id,
                entry_amount, entry_price, split_tx, clob_order_id, clob_filled,
                status, notes, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            entry.position_id,
            entry.agent_id,
            entry.market_id,
            entry.question,
            entry.position,
            entry.token_id,
            entry.entry_amount,
            entry.entry_price,
            entry.split_tx,
            entry.clob_order_id,
            entry.clob_filled,
            entry.status,
            entry.notes,
            datetime.fromisoformat(entry.entry_time) if entry.entry_time else datetime.now(timezone.utc),
        )

    async def get(self, position_id: str) -> Optional[dict]:
        """Get position by ID."""
        pool = get_pool()
        row = await pool.fetchrow("SELECT * FROM positions WHERE position_id = $1", position_id)
        return dict(row) if row else None

    async def get_by_market(self, market_id: str) -> list[dict]:
        """Get all positions for a market."""
        pool = get_pool()
        rows = await pool.fetch("SELECT * FROM positions WHERE market_id = $1", market_id)
        return [dict(r) for r in rows]

    async def get_by_agent(self, agent_id: str) -> list[dict]:
        """Get all positions for an agent."""
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT * FROM positions WHERE agent_id = $1 ORDER BY created_at DESC",
            agent_id,
        )
        return [dict(r) for r in rows]

    async def get_open(self) -> list[dict]:
        """Get all open positions."""
        pool = get_pool()
        rows = await pool.fetch("SELECT * FROM positions WHERE status = 'open' ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    async def update_status(self, position_id: str, status: str) -> bool:
        """Update position status."""
        pool = get_pool()
        result = await pool.execute(
            "UPDATE positions SET status = $1 WHERE position_id = $2",
            status,
            position_id,
        )
        return result == "UPDATE 1"

    async def update_notes(self, position_id: str, notes: str) -> bool:
        """Update position notes."""
        pool = get_pool()
        result = await pool.execute(
            "UPDATE positions SET notes = $1 WHERE position_id = $2",
            notes,
            position_id,
        )
        return result == "UPDATE 1"

    async def count(self) -> int:
        """Get total position count."""
        pool = get_pool()
        return await pool.fetchval("SELECT COUNT(*) FROM positions")


class TradeStorage:
    """PostgreSQL-backed trade recording."""

    async def record(
        self,
        trade_id: str,
        agent_id: str,
        market_id: str,
        question: str,
        side: str,
        amount_usd: float,
        entry_price: float,
        split_tx: Optional[str] = None,
        clob_order_id: Optional[str] = None,
        clob_filled: bool = False,
        status: str = "executed",
        error: Optional[str] = None,
    ) -> None:
        """Record a trade execution."""
        pool = get_pool()
        await pool.execute(
            """
            INSERT INTO trades (
                trade_id, agent_id, market_id, question, side, amount_usd,
                entry_price, split_tx, clob_order_id, clob_filled, status, error
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            trade_id,
            agent_id,
            market_id,
            question,
            side,
            amount_usd,
            entry_price,
            split_tx,
            clob_order_id,
            clob_filled,
            status,
            error,
        )

    async def get_by_agent(self, agent_id: str, limit: int = 50) -> list[dict]:
        """Get trade history for an agent."""
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT * FROM trades WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
            agent_id,
            limit,
        )
        return [dict(r) for r in rows]

    async def get_trade(self, trade_id: str) -> Optional[dict]:
        """Get single trade by ID."""
        pool = get_pool()
        row = await pool.fetchrow("SELECT * FROM trades WHERE trade_id = $1", trade_id)
        return dict(row) if row else None
