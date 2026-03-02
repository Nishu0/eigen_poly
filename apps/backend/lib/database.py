"""Database connection pool and schema management using asyncpg."""

import os
from contextlib import asynccontextmanager

import asyncpg


_pool: asyncpg.Pool | None = None


SCHEMA_SQL = """
-- Users (Google OAuth accounts)
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    google_sub TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Registered agents
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL,
    api_key_hash TEXT UNIQUE NOT NULL,
    wallet_index INTEGER DEFAULT 0,
    polygon_safe TEXT DEFAULT '',
    solana_vault TEXT DEFAULT '',
    scopes TEXT[] DEFAULT ARRAY['trade','balance','markets'],
    owner_id TEXT REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Device codes (agent claim flow)
CREATE TABLE IF NOT EXISTS device_codes (
    device_code TEXT PRIMARY KEY,
    user_code TEXT UNIQUE NOT NULL,
    agent_id TEXT REFERENCES agents(agent_id),
    status TEXT DEFAULT 'pending',
    user_id TEXT REFERENCES users(user_id),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade executions
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(agent_id),
    market_id TEXT NOT NULL,
    question TEXT,
    side TEXT NOT NULL,
    amount_usd DOUBLE PRECISION NOT NULL,
    entry_price DOUBLE PRECISION,
    split_tx TEXT,
    clob_order_id TEXT,
    clob_filled BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'executed',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Open positions
CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(agent_id),
    market_id TEXT NOT NULL,
    question TEXT,
    position TEXT NOT NULL,
    token_id TEXT,
    entry_amount DOUBLE PRECISION,
    entry_price DOUBLE PRECISION,
    split_tx TEXT,
    clob_order_id TEXT,
    clob_filled BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'open',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent API request logs (every route hit via API key)
CREATE TABLE IF NOT EXISTS agent_logs (
    log_id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(agent_id),
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    ip_address TEXT,
    body_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agents_api_key_hash ON agents(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_agents_wallet ON agents(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agents_owner ON agents(owner_id);
CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_id);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_positions_agent ON positions(agent_id);
CREATE INDEX IF NOT EXISTS idx_positions_market ON positions(market_id);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created ON agent_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_codes_user_code ON device_codes(user_code);
CREATE INDEX IF NOT EXISTS idx_device_codes_agent ON device_codes(agent_id);
"""


async def init_db() -> asyncpg.Pool:
    """Create connection pool and run schema migration."""
    global _pool

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )

    # Run schema migration
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)

    return _pool


async def close_db() -> None:
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the active connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _pool
