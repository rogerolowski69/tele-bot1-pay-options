# telegram-payments-app

Monorepo for a Telegram bot + Mini App with three payment paths:

1. **Telegram Stars** (`XTR`) — digital goods inside Telegram
2. **Telegram provider / card** — physical or off-Stars goods via `provider_token`
3. **External crypto** — NOWPayments (BTCPay/KHQR adapters can plug in similarly)

## Structure

```
telegram-payments-app/
├── apps/
│   ├── miniapp/          # React + Vite Telegram Mini App
│   ├── bot/              # aiogram 3.x bot
│   └── api/              # FastAPI backend
├── packages/
│   ├── shared_types/     # PaymentMethod, OrderStatus, etc.
│   ├── telegram_auth/    # initData HMAC verifier
│   └── market_data/      # SEC EDGAR, yfinance, CoinGecko aggregator
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.debug.yml   # Adminer, Redis Commander, Dozzle, Mailpit
│   ├── nginx.conf
│   └── db/init.sql
└── pyproject.toml        # Python deps (uv)
```

## Payment flow

```
User → Bot → Mini App → POST /api/checkout → Order in Postgres
  → Telegram invoice (openInvoice) or external URL (openLink)
  → Bot successful_payment / provider webhook → mark paid in API
  → Deliver product (backend only)
```

**Frontend `openInvoice` callback is UX only.** Webhooks and bot `successful_payment` are the source of truth.

## Market data aggregator

Two-zone architecture keeps the bot responsive and respects upstream rate limits:

```
Telegram user  (/crypto, /stock, /options, /fundamentals)
        │
        ▼
  Bot handlers  →  API /api/market/*
        │
   ┌────┴────┐
   ▼         ▼
Market zone   Fundamental zone
(Redis 60s)   (Redis 1h)
├ CoinGecko   ├ SEC EDGAR (XBRL, 8 req/s)
├ yfinance    └ yfinance financials
├ Alpha Vantage (optional)
└ Polygon.io (optional)
```

### Bot commands

| Command | Example | Source |
|---------|---------|--------|
| `/crypto` | `/crypto bitcoin` | CoinGecko |
| `/stock` | `/stock AAPL` | yfinance |
| `/options` | `/options AAPL` | yfinance option chain |
| `/fundamentals` | `/fundamentals AAPL` | SEC EDGAR + yfinance |
| `/sec` | `/sec AAPL` | alias for `/fundamentals` |
| `/market` | — | help text |

### SEC EDGAR setup (required for `/sec`)

The SEC blocks requests without a proper `User-Agent`. Set in `.env`:

```
SEC_USER_AGENT=YourName sbgreenland@gmail.com
```

Max **10 requests/second** — the client rate-limits to 8/sec and caches fundamentals in Redis for 1 hour.

### Optional API keys

```
COINGECKO_API_KEY=        # optional pro tier
ALPHA_VANTAGE_API_KEY=    # fallback stock quotes
POLYGON_API_KEY=          # end-of-day reference prices
```

## Quick start (Docker + uv)

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`). Docker images install deps via `uv sync --frozen`.

```bash
cp .env.example .env
# Set BOT_TOKEN (and optionally TELEGRAM_PROVIDER_TOKEN, NOWPAYMENTS_*)

cd infra
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

| Service          | URL                    |
|------------------|------------------------|
| App (nginx)      | http://localhost:8080 (set `NGINX_PORT` in `.env`) |
| API              | http://localhost:8000  |
| API docs (debug) | http://localhost:8000/docs |
| Mini App (dev)   | http://localhost:5173  |
| Adminer (DB)     | http://localhost:8081  |
| Redis Commander  | http://localhost:8084  |
| Dozzle (logs)    | http://localhost:8083  |
| Mailpit (email)  | http://localhost:8025  |

**Quick start script (Windows — run from repo root):**

```powershell
cd C:\Users\roger\Documents\code\telegram-bot\bot1-pay-options
.\dev-up.ps1
```

If you get "not recognized", you are in the wrong folder. Use `.\` (backslash), not `./`.

**Infra + debug tools only** (run API/bot locally with uv):

```powershell
.\dev-infra.ps1 -d    # Windows
```

### Debug tools

| Tool | Purpose |
|------|---------|
| **Adminer** | Browse/edit Postgres (`postgres` / `postgres` / `telegram_payments`) |
| **Redis Commander** | Inspect cache keys, idempotency locks |
| **Dozzle** | Live Docker container logs |
| **Mailpit** | Catch outbound SMTP (UI on :8025, SMTP on :1025) |
| **FastAPI `/docs`** | Swagger UI when `DEBUG=true` |
| **`/api/debug/*`** | Test initData, list orders, simulate payment |

Debug API routes (404 when `DEBUG=false`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/debug/health` | Postgres + Redis connectivity |
| POST | `/api/debug/init-data` | Generate valid `X-Telegram-Init-Data` for curl/Postman |
| GET | `/api/debug/orders` | List recent orders |
| POST | `/api/debug/orders/{id}/simulate-payment` | Mark order paid without Telegram |

See `scripts/debug-api.http` for copy-paste examples.

**Adminer:** System `PostgreSQL`, server `postgres`, user/pass/db from `.env` (default `postgres` / `postgres` / `telegram_payments`).

Production without debug tools:

```bash
docker compose up --build
```

## Local dev (uv, without Docker)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then from the repo root:

```bash
uv sync
cp .env.example .env
# edit .env — set BOT_TOKEN, DATABASE_URL, REDIS_URL for localhost
```

Start Postgres + Redis + debug tools (run API/bot locally with uv):

```powershell
.\dev-infra.ps1 -d    # Windows
```

**API**

```bash
uv run uvicorn apps.api.main:app --reload --port 8000
```

**Bot**

```bash
uv run python -m apps.bot.main
```

**Mini App**

```bash
cd apps/miniapp
npm install
npm run dev
```

Add a dependency:

```bash
uv add httpx
# commit pyproject.toml + uv.lock
```

## Tests

```powershell
.\test.ps1
# or
uv sync --group dev
uv run pytest tests/ -v
```

Coverage includes initData verification, checkout auth rules, webhook secrets, order payment logic, and health/readiness endpoints.

## Security checklist

- [x] Verify `X-Telegram-Init-Data` on every checkout request
- [x] Package prices loaded from DB (never from frontend)
- [x] Order created before invoice
- [x] Payload format `order:<uuid>`
- [x] Redis lock + idempotency on mark paid
- [x] Amount + currency match before `paid`
- [x] Raw webhook JSON stored in `orders.raw_provider_payload`
- [x] NOWPayments signature verification (when secret set)
- [x] Digital goods restricted to Stars in checkout route

## API

| Method | Path                         | Description              |
|--------|------------------------------|--------------------------|
| GET    | `/api/packages`              | List active packages     |
| POST   | `/api/checkout`              | Create order + invoice   |
| POST   | `/api/webhooks/telegram/payment` | Bot payment confirm  |
| POST   | `/api/webhooks/nowpayments`  | Crypto IPN               |
| GET    | `/health`                    | Liveness (process up)    |
| GET    | `/ready`                     | Readiness (Postgres+Redis) |

### Checkout example

```json
POST /api/checkout
Headers: X-Telegram-Init-Data: <initData>

{
  "package_id": "starter",
  "method": "stars"
}
```

Response:

```json
{
  "type": "telegram_invoice",
  "url": "https://t.me/$...",
  "order_id": "..."
}
```

## Database

Orders table matches the spec (`pending`, `invoice_created`, `paid`, `failed`, `expired`, `cancelled`, `refunded`). Seed packages in `infra/db/init.sql`.

## Next steps

- **Deploy to Railway:** [docs/railway.md](docs/railway.md)
- Wire BTCPay / KHQR adapters in `apps/api/services/`
- Add refund flow (Stars `refundStarPayment`)
- Point Mini App URL in BotFather to your nginx/public URL
- Replace CORS `*` with your domain in production
