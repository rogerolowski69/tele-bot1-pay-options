"""UTC timestamps compatible with naive and timestamptz Postgres columns."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_db() -> datetime:
    """UTC now as naive datetime for TIMESTAMP WITHOUT TIME ZONE columns.

    After Alembic 0003 (TIMESTAMPTZ), aware UTC is also valid; naive UTC is
    still stored correctly when Postgres session timezone is UTC (Railway default).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
