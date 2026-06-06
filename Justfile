# telegram-payments-app — run `just` or `just --list`
#
# Requires: uv, docker, npm (miniapp), just (https://just.systems)

set dotenv-load

export DOCKER_BUILDKIT := "1"
export COMPOSE_DOCKER_CLI_BUILD := "1"

set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

root := justfile_directory()
infra := root / "infra"
compose := "docker compose -f docker-compose.yml"
compose-debug := compose + " -f docker-compose.debug.yml"
infra-services := "postgres redis adminer redis-commander dozzle mailpit"

default:
    @just --list

alias d := dev
alias t := test
alias u := up

# ─── Setup ───────────────────────────────────────────────────────────────────

[group("setup")]
[doc("Copy .env.example → .env if missing")]
env:
    $envFile = Join-Path "{{root}}" ".env"
    $example = Join-Path "{{root}}" ".env.example"
    if (-not (Test-Path $envFile)) { Copy-Item $example $envFile; Write-Host "Created .env — set BOT_TOKEN" } else { Write-Host ".env already exists" }

[group("setup")]
[doc("Install Python dependencies (uv sync)")]
install:
    cd {{root}}; uv sync

[group("setup")]
[doc("Install Python dev dependencies (pytest, etc.)")]
install-dev:
    cd {{root}}; uv sync --group dev

[group("setup")]
[doc("Install miniapp npm dependencies")]
miniapp-install:
    cd {{root}}/apps/miniapp; npm install

[group("setup")]
[doc("First-time setup: env + dev deps + miniapp")]
setup: env install-dev miniapp-install

[group("setup")]
[doc("Add a Python package (updates pyproject.toml + uv.lock)")]
add PACKAGE:
    cd {{root}}; uv add {{PACKAGE}}

# ─── Docker — full stack ─────────────────────────────────────────────────────

[group("docker")]
[doc("Full dev stack + debug tools (Adminer, Redis Commander, Dozzle, Mailpit)")]
dev *ARGS:
    cd {{infra}}; {{compose-debug}} up --build {{ARGS}}

[group("docker")]
[doc("Production compose (no debug overlay)")]
up *ARGS:
    cd {{infra}}; {{compose}} up --build {{ARGS}}

[group("docker")]
[doc("Stop all services")]
down:
    cd {{infra}}; {{compose-debug}} down

[group("docker")]
[doc("Build all images")]
build:
    cd {{infra}}; {{compose-debug}} build

[group("docker")]
[doc("Rebuild images without cache")]
build-fresh:
    cd {{infra}}; {{compose-debug}} build --no-cache

[group("docker")]
[doc("Follow container logs (optional service name)")]
logs *ARGS:
    cd {{infra}}; {{compose-debug}} logs -f {{ARGS}}

[group("docker")]
[doc("List running containers")]
ps:
    cd {{infra}}; {{compose-debug}} ps

[group("docker")]
[doc("Restart a single service (e.g. just restart api)")]
restart SERVICE:
    cd {{infra}}; {{compose-debug}} restart {{SERVICE}}

# ─── Docker — infra only ─────────────────────────────────────────────────────

[group("docker")]
[doc("Postgres, Redis, and debug UIs only — run api/bot/miniapp locally with uv")]
infra *ARGS:
    cd {{infra}}; {{compose-debug}} up {{infra-services}} {{ARGS}}

[group("docker")]
[doc("Infra in background (-d)")]
infra-d:
    cd {{infra}}; {{compose-debug}} up -d {{infra-services}}

[group("docker")]
[doc("Stop infra services")]
infra-down:
    cd {{infra}}; {{compose-debug}} stop {{infra-services}}

# ─── Local dev (uv + npm, no app containers) ─────────────────────────────────

[group("dev")]
[doc("FastAPI with hot reload on :8000")]
api:
    cd {{root}}; uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

[group("dev")]
[doc("aiogram bot (needs API + BOT_TOKEN)")]
bot:
    cd {{root}}; uv run python -m apps.bot.main

[group("dev")]
[doc("Vite miniapp dev server on :5173")]
miniapp:
    cd {{root}}/apps/miniapp; npm run dev -- --host

[group("dev")]
[doc("Production build of miniapp")]
miniapp-build:
    cd {{root}}/apps/miniapp; npm run build

[group("dev")]
[doc("Miniapp preview (after miniapp-build)")]
miniapp-preview:
    cd {{root}}/apps/miniapp; npm run preview -- --host

# ─── Tests ───────────────────────────────────────────────────────────────────

[group("test")]
[doc("Run pytest suite")]
test *ARGS:
    cd {{root}}; uv run pytest tests/ -v {{ARGS}}

[group("test")]
[doc("Run tests quietly")]
test-quick:
    cd {{root}}; uv run pytest tests/ -q

[group("test")]
[doc("Run a single test file")]
test-file FILE:
    cd {{root}}; uv run pytest {{FILE}} -v

# ─── Health & URLs ───────────────────────────────────────────────────────────

[group("check")]
[doc("API liveness probe")]
health:
    curl -fsS http://localhost:8000/health

[group("check")]
[doc("API readiness probe (Postgres + Redis)")]
ready:
    curl -fsS http://localhost:8000/ready

[group("check")]
[doc("Print local dev URLs")]
urls:
    @Write-Host "App (nginx)     http://localhost:$($env:NGINX_PORT ?? '8080')"
    @Write-Host "API             http://localhost:8000"
    @Write-Host "API docs        http://localhost:8000/docs  (DEBUG=true)"
    @Write-Host "Miniapp (dev)   http://localhost:5173"
    @Write-Host "Adminer         http://localhost:8081"
    @Write-Host "Redis Commander http://localhost:8084"
    @Write-Host "Dozzle          http://localhost:8083"
    @Write-Host "Mailpit         http://localhost:8025"

# ─── Database & Redis ────────────────────────────────────────────────────────

[group("db")]
[doc("Migrate + seed (Alembic + package catalog)")]
db-setup:
    cd {{root}}; uv run python scripts/db_deploy.py

[group("db")]
[doc("Apply Alembic migrations only (requires DATABASE_URL in env)")]
db-migrate:
    cd {{root}}; uv run alembic upgrade head

[group("db")]
[doc("Seed package catalog only (requires DATABASE_URL in env)")]
db-seed:
    cd {{root}}; uv run python scripts/seed_packages.py

[group("db")]
[doc("Autogenerate new Alembic revision from models")]
db-revision MESSAGE:
    cd {{root}}; uv run alembic revision --autogenerate -m "{{MESSAGE}}"

[group("db")]
[doc("Open psql shell in postgres container")]
db-shell:
    cd {{infra}}; docker compose exec postgres psql -U postgres -d telegram_payments

[group("db")]
[doc("Open redis-cli in redis container")]
redis-cli:
    cd {{infra}}; docker compose exec redis redis-cli

[group("db")]
[doc("WARNING: stop stack and delete postgres/redis volumes")]
db-reset:
    cd {{infra}}; {{compose-debug}} down -v

# ─── Acton / TON ───────────────────────────────────────────────────────

[group("ton")]
[doc("Run any acton command (OS-aware: WSL on Windows, native on Linux)")]

[unix]
acton *ARGS:
    bash "{{root}}/scripts/os-run.sh" acton {{ARGS}}

[windows]
acton *ARGS:
    pwsh -NoLogo -File "{{root}}/scripts/os-run.ps1" acton {{ARGS}}

[group("ton")]
[doc("Run Acton contract tests")]

[unix]
acton-test:
    bash "{{root}}/scripts/os-run.sh" acton-test

[windows]
acton-test:
    pwsh -NoLogo -File "{{root}}/scripts/os-run.ps1" acton-test

[group("ton")]
[doc("Deploy contracts to local emulation")]

[unix]
acton-deploy-emulation:
    bash "{{root}}/scripts/os-run.sh" acton-deploy-emulation

[windows]
acton-deploy-emulation:
    pwsh -NoLogo -File "{{root}}/scripts/os-run.ps1" acton-deploy-emulation

[group("ton")]
[doc("Deploy contracts to TON testnet")]

[unix]
acton-deploy-testnet:
    bash "{{root}}/scripts/os-run.sh" acton-deploy-testnet

[windows]
acton-deploy-testnet:
    pwsh -NoLogo -File "{{root}}/scripts/os-run.ps1" acton-deploy-testnet

# ─── Git / deploy helpers ────────────────────────────────────────────────────

[group("deploy")]
[doc("Show Railway deploy docs path")]
railway-docs:
    @Write-Host "See docs/railway.md for Railway setup (api + bot + miniapp services)"
