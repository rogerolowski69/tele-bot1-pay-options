# telegram-payments-app

Monorepo for a Telegram bot + Mini App with **Stars** and **TON** payments, plus optional market-data bot commands.

## Structure

```
telegram-payments-app/
├── apps/
│   ├── miniapp/          # React + Vite + @telegram-apps/sdk + TonConnect
│   ├── bot/              # aiogram 3.x bot
│   └── api/              # FastAPI backend
├── packages/
│   ├── shared_types/     # PaymentMethod, OrderStatus, etc.
│   ├── telegram_auth/    # initData HMAC verifier
│   └── market_data/      # SEC EDGAR, yfinance, CoinGecko aggregator
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.debug.yml
│   ├── nginx.conf
│   └── db/init.sql
├── Justfile              # just --list for all commands
└── pyproject.toml        # Python deps (uv)
```

## Payment flows (Stars + TON)

### Stars (digital goods)

```
User → Mini App → POST /api/checkout (method: stars)
     → openInvoice → Telegram payment
     → Bot pre_checkout validates order with API
     → Bot successful_payment → API mark paid → delivery DM
     → Mini App polls until paid → success page
```

### TON (non-digital / off-platform)

```
User → Mini App → POST /api/checkout (method: ton)
     → TonConnect send tx (comment: order:<uuid>)
     → POST /api/checkout/ton/confirm (on-chain verify via TonAPI)
     → mark paid → delivery DM
     → Success page + My purchases
```

**Frontend callbacks are UX only.** Webhooks, bot `successful_payment`, and on-chain confirmation are the source of truth.

## Quick start

Requires: Docker, [uv](https://docs.astral.sh/uv/), Node 22+, [just](https://just.systems) (optional).

**Windows (PowerShell):**

```powershell
cp .env.example .env
# Set BOT_TOKEN, WEBHOOK_SECRET, TON_RECEIVE_ADDRESS, TON_PACKAGE_PRICES

just setup
just dev
# or: .\dev-up.ps1  |  .\task.ps1 dev-up
```

**Linux / macOS:**

```bash
cp .env.example .env
just setup
just dev
# or: ./dev-up.sh  |  ./task.sh dev-up
```

Both platforms use paired scripts (`.ps1` + `.sh`). Root wrappers delegate to `scripts/`; `task.ps1` / `task.sh` pick the right one via `scripts/os-run.*`.

| Service          | URL |
|------------------|-----|
| App (nginx)      | http://localhost:8080 (`NGINX_PORT` in `.env`) |
| API              | http://localhost:8000 |
| Mini App (dev)   | http://localhost:5173 |
| Adminer          | http://localhost:8081 |

### Required `.env` for Stars + TON

```env
BOT_TOKEN=your_bot_token
WEBHOOK_SECRET=random_shared_secret
MINI_APP_URL=http://localhost:8080

# TON merchant wallet (testnet while developing)
TON_RECEIVE_ADDRESS=EQ...
TON_NETWORK=testnet
TON_PACKAGE_PRICES={"pro":500000000}
```

### Packages (seed data)

| ID | Payment | Price |
|----|---------|-------|
| `starter` | Stars only (digital) | 100 ⭐ |
| `pro` | TON | 0.5 TON via `TON_PACKAGE_PRICES` |
| `ton_pack` | TON | 0.1 TON (currency=TON in DB) |

Each package has a `delivery_content` message sent to the user's Telegram chat after payment.

## Deploy checklist (production)

1. **HTTPS URL** — Telegram Mini Apps require HTTPS (not localhost on a phone).
2. **BotFather** — Set Mini App URL to your public nginx/miniapp domain.
3. **TonConnect manifest** — Update `apps/miniapp/public/tonconnect-manifest.json` (`url` + `iconUrl`) or set `VITE_MINIAPP_ORIGIN` at build time.
4. **Database** — If upgrading an existing DB, run:
   ```sql
   ALTER TABLE packages ADD COLUMN IF NOT EXISTS delivery_content TEXT NOT NULL DEFAULT '';
   ```
5. **Env on host/Railway** — `BOT_TOKEN`, `WEBHOOK_SECRET`, `TON_RECEIVE_ADDRESS`, `API_BASE_URL`, `MINI_APP_URL`.
6. **Test** — One Stars purchase (`starter`) + one TON purchase (`pro` or `ton_pack`).

See [docs/railway.md](docs/railway.md) for Railway (api + bot + miniapp services).

## Mini App pages

| Route | Purpose |
|-------|---------|
| `/` | Shop — Stars (digital) or TON |
| `/orders` | Purchase history + resume pending TON |
| `/checkout/ton?order_id=` | TON payment (works after refresh) |
| `/success?order_id=` | Delivery content |

Bot command `/orders` opens the purchase history page in the mini app.

## API (Stars + TON)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/packages` | List packages |
| GET | `/api/config/payments` | `{ stars, ton }` enabled flags |
| POST | `/api/checkout` | Create order + invoice (initData required) |
| GET | `/api/orders/me` | User's order history |
| GET | `/api/orders/{id}` | Order detail + delivery |
| GET | `/api/orders/{id}/ton-payment` | Resume TON checkout payload |
| POST | `/api/checkout/ton/confirm` | Verify on-chain TON payment |
| POST | `/api/internal/pre-checkout` | Bot validates before Telegram checkout |
| POST | `/api/webhooks/telegram/payment` | Bot payment confirmation |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (Postgres + Redis) |

## Scripts (Windows ↔ Linux)

| Task | Windows | Linux / macOS | Notes |
|------|---------|---------------|-------|
| Full dev stack | `.\dev-up.ps1` | `./dev-up.sh` | Docker BuildKit enabled |
| Infra only | `.\dev-infra.ps1` | `./dev-infra.sh` | Postgres, Redis, debug UIs |
| Tests | `.\test.ps1` | `./test.sh` | `uv run pytest` |
| Any task (OS pick) | `.\task.ps1 <task>` | `./task.sh <task>` | Uses `scripts/os-run.*` |
| Acton CLI | `.\acton.ps1 test` | `./acton.sh test` | WSL on Windows |
| Acton tests | `.\task.ps1 acton-test` | `./task.sh acton-test` | |

`scripts/os-run.ps1` / `scripts/os-run.sh` run the matching `.ps1` on Windows and `.sh` elsewhere. Railway deploy scripts under `scripts/railway/` are Linux-only (container entrypoints).

## Commands (just)

```powershell
just dev          # Full Docker stack + debug tools
just test         # pytest
just api          # API only (local uv)
just miniapp      # Vite dev server
just urls         # Print local URLs
```

## Tests

```powershell
just test
# 36+ tests — initData, checkout, Stars pre-checkout, TON verify, fulfillment, order history
```

## Security checklist

- [x] Verify `X-Telegram-Init-Data` on checkout and order routes
- [x] Package prices from DB only
- [x] Order created before invoice
- [x] Bot pre_checkout validates amount/currency/status with API
- [x] Redis lock + idempotent `mark_paid`
- [x] Delivery sent once per order (Telegram DM)
- [x] Digital goods restricted to Stars

## Market data (optional)

The bot also supports `/crypto`, `/stock`, `/options`, `/fundamentals`, `/sec`. Set `SEC_USER_AGENT=YourName email@example.com` for SEC EDGAR.

## Also in repo (optional)

- NOWPayments / card checkout (API exists; shop UI focuses on Stars + TON)
- `ton/` Acton counter dApp (separate TON demo, not the payment shop)

## Completeness

**Ready for local dev and production deploy (with your env):**

- Stars checkout, pre-checkout validation, fulfillment DMs
- TON checkout, TonConnect, on-chain confirm, resume after refresh
- Order history (mini app + `/orders` bot command)
- Docker Compose dev stack, Adminer, tests (40+)
- Paired `.ps1` / `.sh` scripts with OS-aware runners
- Order expiry + delivery retry (API background task)

**Not included (optional / future):**

- Refunds (`refundStarPayment`)
- Alembic migrations (schema via `infra/db/init.sql` + manual ALTER)
- CI/CD pipeline
- Card / NOWPayments in shop UI (API stubs exist; IPN signature verified)
- `ton/` Acton counter is a separate demo, not wired to the payment shop

Production still requires you to configure HTTPS, BotFather mini app URL, `TON_RECEIVE_ADDRESS`, and TonConnect manifest — see deploy checklist above.

## Future improvements

- Refunds (Stars `refundStarPayment`)
- Alembic migrations
- Rich delivery (files, license keys, role grants)
- GitHub Actions CI
