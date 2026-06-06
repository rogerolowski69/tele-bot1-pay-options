import asyncio
import os

import asyncpg

PACKAGES = [
    {
        "id": "starter",
        "title": "Starter Package",
        "description": "Digital starter package",
        "delivery_content": "Your Starter pack is active. Welcome aboard!",
        "amount_minor": 100,
        "currency": "XTR",
        "is_digital": True,
    },
    {
        "id": "pro",
        "title": "Pro Package",
        "description": "Physical / off-platform package (USD card, crypto, or TON)",
        "delivery_content": "Your Pro access is unlocked. Check your email for next steps.",
        "amount_minor": 500,
        "currency": "USD",
        "is_digital": False,
    },
    {
        "id": "ton_pack",
        "title": "TON Package",
        "description": "Package priced in TON",
        "delivery_content": "Your TON purchase is complete. Enjoy your package!",
        "amount_minor": 100_000_000,
        "currency": "TON",
        "is_digital": False,
    },
]


def normalize_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    conn = await asyncpg.connect(normalize_url(os.environ["DATABASE_URL"]))

    try:
        for package in PACKAGES:
            await conn.execute(
                """
                INSERT INTO packages (
                    id, title, description, delivery_content,
                    amount_minor, currency, is_digital
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    delivery_content = EXCLUDED.delivery_content,
                    amount_minor = EXCLUDED.amount_minor,
                    currency = EXCLUDED.currency,
                    is_digital = EXCLUDED.is_digital,
                    active = true
                """,
                package["id"],
                package["title"],
                package["description"],
                package["delivery_content"],
                package["amount_minor"],
                package["currency"],
                package["is_digital"],
            )

        print("Seeded packages.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
