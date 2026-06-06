from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._env import ensure_database_url


def normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
        .replace("postgres+psycopg://", "postgresql://")
    )


async def main() -> None:
    db_url = ensure_database_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL missing")

    conn = await asyncpg.connect(normalize_url(db_url))
    try:
        rows = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        if not rows:
            print("(no public tables)")
            return

        for row in rows:
            print(row["table_name"])
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
