#!/usr/bin/env python3
"""Database management script — reset, migrate, and inspect tables.

Usage:
    # Reset DB (drop + recreate all tables)
    .venv/bin/python scripts/db.py reset

    # Migrate (create tables if not exist, safe to run repeatedly)
    .venv/bin/python scripts/db.py migrate

    # Show current tables and row counts
    .venv/bin/python scripts/db.py status
"""

import sys
import asyncio
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncpg

from lib.database import SCHEMA_SQL


DROP_SQL = """
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
"""


async def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Error: DATABASE_URL not set in .env")
        sys.exit(1)
    return await asyncpg.connect(url)


async def cmd_reset():
    """Drop all tables and recreate from scratch."""
    conn = await get_conn()
    print("Dropping tables...")
    await conn.execute(DROP_SQL)
    print("Creating tables...")
    await conn.execute(SCHEMA_SQL)
    print("Done! Tables reset.")
    await show_status(conn)
    await conn.close()


async def cmd_migrate():
    """Create tables if they don't exist (safe to run repeatedly)."""
    conn = await get_conn()
    print("Running migrations...")
    await conn.execute(SCHEMA_SQL)
    print("Done! Schema up to date.")
    await show_status(conn)
    await conn.close()


async def show_status(conn):
    """Show tables and row counts."""
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    print(f"\nTables in DB:")
    for t in tables:
        name = t["tablename"]
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {name}")
        print(f"  {name:20s} {count} rows")


async def cmd_status():
    """Show current DB status."""
    conn = await get_conn()
    await show_status(conn)

    # Show columns for our tables
    for t in ["agents", "trades", "positions"]:
        cols = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name = '{t}' ORDER BY ordinal_position"
        )
        if cols:
            print(f"\n{t} columns:")
            for c in cols:
                print(f"  {c['column_name']:20s} {c['data_type']}")

    await conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/db.py <command>")
        print("Commands: reset, migrate, status")
        return 1

    cmd = sys.argv[1]
    if cmd == "reset":
        asyncio.run(cmd_reset())
    elif cmd == "migrate":
        asyncio.run(cmd_migrate())
    elif cmd == "status":
        asyncio.run(cmd_status())
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: reset, migrate, status")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
