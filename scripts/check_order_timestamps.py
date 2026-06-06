from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

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


def require_reachable_database_url() -> str:
    url = ensure_database_url()
    host = urlparse(normalize_url(url)).hostname or ""
    if host.endswith(".railway.internal"):
        print(
            "DATABASE_URL uses Railway private DNS "
            f"({host}).\n"
            "railway run executes on your machine — it cannot reach that host.\n\n"
            "Verify from production instead:\n"
            "  curl.exe -s $API/api/debug/order-timestamp-columns\n\n"
            "Or enable Postgres TCP Proxy in Railway and use the public URL locally.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


async def main() -> None:
    conn = await asyncpg.connect(normalize_url(require_reachable_database_url()))
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
