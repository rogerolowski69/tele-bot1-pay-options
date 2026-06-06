"""Railway pre-deploy: adopt existing schema if needed, migrate, seed."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._env import ensure_database_url


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, check=True, env=os.environ.copy())


def alembic_current() -> str:
    result = subprocess.run(
        ["uv", "run", "alembic", "current"],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        print(result.stderr, flush=True)
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result.stdout


def tables_exist() -> bool:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/list_tables.py"],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        print(result.stderr, flush=True)
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return "packages" in names and "orders" in names


def main() -> None:
    ensure_database_url()
    current = alembic_current()
    has_revision = any(
        rev in current
        for rev in (
            "0001_create_packages_orders",
            "0002_order_timestamps_tz",
            "0003_ensure_timestamptz",
        )
    )

    if tables_exist() and not has_revision:
        run(["uv", "run", "alembic", "stamp", "0001_create_packages_orders"])

    run(["uv", "run", "alembic", "upgrade", "head"])
    run(["uv", "run", "python", "scripts/seed_packages.py"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
