-- Packages catalog (server-side prices — never trust frontend)
CREATE TABLE IF NOT EXISTS packages (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    amount_minor INTEGER NOT NULL,
    currency    TEXT NOT NULL,
    is_digital  BOOLEAN NOT NULL DEFAULT true,
    active      BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO packages (id, title, description, amount_minor, currency, is_digital) VALUES
    ('starter', 'Starter Package', 'Digital starter package', 100, 'XTR', true),
    ('pro', 'Pro Package', 'Digital pro package', 500, 'USD', false)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS orders (
    id                   UUID PRIMARY KEY,
    telegram_user_id     BIGINT NOT NULL,
    package_id           TEXT NOT NULL REFERENCES packages(id),

    payment_method       TEXT NOT NULL,
    provider             TEXT NOT NULL,
    provider_invoice_id  TEXT,
    provider_charge_id   TEXT,

    amount_minor         INTEGER NOT NULL,
    currency             TEXT NOT NULL,

    status               TEXT NOT NULL DEFAULT 'pending',
    idempotency_key      TEXT UNIQUE NOT NULL,

    raw_provider_payload JSONB DEFAULT '{}'::jsonb,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at              TIMESTAMPTZ,
    failed_at            TIMESTAMPTZ,
    refunded_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_telegram_user ON orders (telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_provider_invoice ON orders (provider, provider_invoice_id);
