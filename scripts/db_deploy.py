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


def main() -> None:
    ensure_database_url()
    run(["uv", "run", "alembic", "upgrade", "head"])
    run(["uv", "run", "python", "scripts/seed_packages.py"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
