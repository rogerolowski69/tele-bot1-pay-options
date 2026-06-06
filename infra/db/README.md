# Database setup

One system owns the database — no duplicate chefs.

| Layer | Tool | Owns |
|-------|------|------|
| **Schema** | Alembic (`migrations/versions/`) | Tables, columns, indexes, constraints |
| **Seed data** | `scripts/seed_packages.py` | `starter`, `pro`, `ton_pack` package rows |
| **Reference** | `init.sql` | Historical schema snapshot — **not** auto-run |

## Local (Docker)

```powershell
just infra-d          # Postgres + Redis
just db-setup         # alembic upgrade head + seed
```

Fresh volume — one command:

```powershell
just db-reset-dev
```

Or step by step:

```powershell
just db-reset
just infra-d
just db-setup
```

## Railway (DB already created from old init.sql)

Stamp once (local against Railway `DATABASE_URL`, or via CLI):

```powershell
just db-stamp-existing
# railway run --service tele-bot1-pay-options just db-stamp-existing
```

After that, pre-deploy runs `scripts/db_deploy.py` safely on every deploy.

## Railway (fresh DB)

```powershell
railway run --service tele-bot1-pay-options uv run python scripts/db_deploy.py
```

## New schema changes

```powershell
just db-revision "describe change"
just db-migrate
```

Commit the new file under `migrations/versions/`.
