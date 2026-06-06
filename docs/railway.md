# Deploy on Railway

This guide deploys **three services** from one GitHub repo plus managed Postgres and Redis.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   miniapp   │────▶│     api     │────▶│  Postgres    │
│  (public)   │     │  (public)   │     │  + Redis     │
└─────────────┘     └──────▲──────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │     bot     │
                    │  (worker)   │
                    └─────────────┘
```

## 1. Create Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select this repository

## 2. Add databases

In the project canvas:

- **+ New** → **Database** → **PostgreSQL**
- **+ New** → **Database** → **Redis**

## 3. Create three services (same repo)

Duplicate the GitHub service twice so you have **api**, **bot**, and **miniapp**.

For each service, open **Settings**:

| Service | Config file path | Railpack config (build var) | Public networking |
|---------|------------------|----------------------------|-------------------|
| **api** | `infra/railway/api.toml` | (uses root `railpack.json`) | ✅ Generate domain |
| **bot** | `infra/railway/bot.toml` | `RAILPACK_CONFIG_FILE=infra/railway/railpack-bot.json` | ❌ None (worker) |
| **miniapp** | `infra/railway/miniapp.toml` | — (Dockerfile) | ✅ Generate domain |

Railpack cannot auto-detect this monorepo’s FastAPI entry (`apps/api/main.py`). The root **`railpack.json`** sets the API start command. The bot service needs its own Railpack config via the build variable above.

## 4. Wire environment variables

### API service

Reference Postgres and Redis from Railway plugins (**Variables** → **Add reference**).

| Variable | Value |
|----------|--------|
| `BOT_TOKEN` | Your Telegram bot token |
| `DATABASE_URL` | Reference → Postgres `DATABASE_URL` |
| `REDIS_URL` | Reference → Redis `REDIS_URL` |
| `DEBUG` | `false` |
| `WEBHOOK_SECRET` | Random secret (same on bot) |
| `SEC_USER_AGENT` | `YourName email@example.com` |
| `API_BASE_URL` | `https://<api-service>.up.railway.app` |
| `NOWPAYMENTS_*` | Optional |

`start-api.sh` rewrites `postgresql://` → `postgresql+asyncpg://` automatically.

### Bot service

| Variable | Value |
|----------|--------|
| `BOT_TOKEN` | Same as API |
| `API_BASE_URL` | `https://<api-service>.up.railway.app` |
| `MINI_APP_URL` | `https://<miniapp-service>.up.railway.app` |
| `WEBHOOK_SECRET` | Same as API |
| `DEBUG` | `false` |

### Mini App service

| Variable | Value |
|----------|--------|
| `API_UPSTREAM` | `https://<api-service>.up.railway.app` |
| `PORT` | Railway sets this automatically |

The miniapp nginx template proxies `/api/*` to `API_UPSTREAM`, so the React app keeps using relative `/api/...` paths.

## 5. Database migrations and seed (automatic on deploy)

The API service config (`infra/railway/api.toml` or root `railway.json`) runs **before each deploy**:

```toml
preDeployCommand = ["uv run python scripts/db_deploy.py"]
```

This applies Alembic migrations, then upserts the package catalog. If pre-deploy fails, Railway blocks the deploy.

**Manual (local or one-off):**

```bash
export DATABASE_URL="postgresql://..."   # or postgresql+asyncpg://...
just db-setup
# or: uv run python scripts/db_deploy.py
```

**Existing Railway DB already created from `init.sql`:** stamp Alembic once, then seed:

```bash
railway run --service tele-bot1-pay-options uv run alembic stamp head
railway run --service tele-bot1-pay-options uv run python scripts/seed_packages.py
```

**Fresh DB:**

```bash
railway run --service tele-bot1-pay-options uv run python scripts/db_deploy.py
```

## 6. Telegram / BotFather

1. [@BotFather](https://t.me/BotFather) → your bot → **Bot Settings** → **Menu Button** / **Web App**
2. Set Mini App URL to: `https://<miniapp-service>.up.railway.app`
3. Ensure `MINI_APP_URL` in the bot service matches exactly

## 7. Deploy order

1. Postgres + Redis (plugins)
2. **api** — pre-deploy runs migrations + seed; wait until `/ready` returns 200
3. **bot** + **miniapp**

Check logs in Railway dashboard or Dozzle locally.

## 8. Verify

| Check | URL / action |
|-------|----------------|
| API ready | `https://<api>.up.railway.app/ready` |
| Packages | `https://<api>.up.railway.app/api/packages` |
| Mini App | Open `https://<miniapp>.up.railway.app` in browser |
| Bot | Telegram → `/start`, `/crypto bitcoin`, Open Shop |
| Swagger | Disabled when `DEBUG=false` |

## Production notes

- Do **not** set `DEBUG=true` on Railway
- Bot uses **long polling** — no webhook URL needed for basic setup
- Mini App **requires HTTPS** — Railway provides this on `*.up.railway.app`
- The dev `docker-compose` stack (Adminer, Dozzle, etc.) is for local use only
- TON/Acton contracts in `ton/` are deployed separately (WSL + `acton`), not on Railway

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **Railpack: No start command detected** | Root `railpack.json` defines `uvicorn apps.api.main:app` via `scripts/railway/start-api.sh`. Set config file path to `infra/railway/api.toml`, or redeploy after pulling latest. Bot service: add `RAILPACK_CONFIG_FILE=infra/railway/railpack-bot.json`. |
| API crash on start | Check `DATABASE_URL` / `REDIS_URL` references |
| Bot can't reach API | `API_BASE_URL` must be public API HTTPS URL |
| Mini App checkout 401 | Open inside Telegram (needs `initData`), not plain browser |
| Mini App API 502 | Set `API_UPSTREAM` to API public URL with `https://` |
| SEC `/fundamentals` fails | Set `SEC_USER_AGENT` on API service |

## Cost tip

Minimum running services: Postgres + Redis + api + bot + miniapp. Consider sleeping non-prod projects or using Railway's usage limits.
