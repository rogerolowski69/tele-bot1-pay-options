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
    conn = await asyncpg.connect(normalize_url(ensure_database_url()))
    try:
        rows = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orders'
              AND column_name IN ('created_at', 'paid_at', 'failed_at', 'refunded_at')
            ORDER BY column_name;
        """)

        for row in rows:
            print(row["column_name"], "=>", row["data_type"])
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
