from __future__ import annotations

import subprocess
import sys


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    run(["uv", "run", "alembic", "upgrade", "head"])
    run(["uv", "run", "python", "scripts/seed_packages.py"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
