"""ensure all order and package timestamps are timestamptz

Revision ID: 0003_ensure_timestamptz
Revises: 0002_order_timestamps_tz
Create Date: 2026-06-06

Idempotent: skips columns already stored as timestamp with time zone.
"""

from __future__ import annotations

from alembic import op

revision = "0003_ensure_timestamptz"
down_revision = "0002_order_timestamps_tz"
branch_labels = None
depends_on = None

_TIMESTAMP_COLUMNS: dict[str, tuple[str, ...]] = {
    "orders": ("created_at", "paid_at", "failed_at", "refunded_at"),
    "packages": ("created_at",),
}


def _alter_to_timestamptz(table: str, column: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table}'
                  AND column_name = '{column}'
                  AND data_type = 'timestamp without time zone'
            ) THEN
                ALTER TABLE {table}
                ALTER COLUMN {column}
                TYPE TIMESTAMPTZ
                USING {column} AT TIME ZONE 'UTC';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            _alter_to_timestamptz(table, column)


def downgrade() -> None:
    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            op.execute(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = '{table}'
                          AND column_name = '{column}'
                          AND udt_name = 'timestamptz'
                    ) THEN
                        ALTER TABLE {table}
                        ALTER COLUMN {column}
                        TYPE TIMESTAMP
                        USING {column} AT TIME ZONE 'UTC';
                    END IF;
                END $$;
                """
            )
