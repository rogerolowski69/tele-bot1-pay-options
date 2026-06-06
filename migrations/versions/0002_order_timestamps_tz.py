"""make order timestamps timezone aware

Revision ID: 0002_order_timestamps_tz
Revises: 0001_create_packages_orders
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op

revision = "0002_order_timestamps_tz"
down_revision = "0001_create_packages_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("created_at", "paid_at", "failed_at", "refunded_at"):
        op.execute(
            f"""
            ALTER TABLE orders
            ALTER COLUMN {col}
            TYPE TIMESTAMPTZ
            USING {col} AT TIME ZONE 'UTC'
            """
        )


def downgrade() -> None:
    for col in ("created_at", "paid_at", "failed_at", "refunded_at"):
        op.execute(
            f"""
            ALTER TABLE orders
            ALTER COLUMN {col}
            TYPE TIMESTAMP
            USING {col} AT TIME ZONE 'UTC'
            """
        )
