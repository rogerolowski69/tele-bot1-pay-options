from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def ensure_database_url() -> str:
    """Load DATABASE_URL from env, repo .env, or local Docker default."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    repo_root = Path(__file__).resolve().parent.parent
    _load_dotenv(repo_root / ".env")

    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_payments"
        )

    return os.environ["DATABASE_URL"]
