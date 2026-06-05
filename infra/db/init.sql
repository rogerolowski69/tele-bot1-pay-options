-- Packages catalog (server-side prices — never trust frontend)
CREATE TABLE IF NOT EXISTS packages (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    delivery_content TEXT NOT NULL DEFAULT '',
    amount_minor INTEGER NOT NULL,
    currency    TEXT NOT NULL,
    is_digital  BOOLEAN NOT NULL DEFAULT true,
    active      BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE packages ADD COLUMN IF NOT EXISTS delivery_content TEXT NOT NULL DEFAULT '';

INSERT INTO packages (id, title, description, delivery_content, amount_minor, currency, is_digital) VALUES
    (
        'starter',
        'Starter Package',
        'Digital starter package',
        'Your Starter pack is active. Welcome aboard!',
        100,
        'XTR',
        true
    ),
    (
        'pro',
        'Pro Package',
        'Physical / off-platform package (USD card, crypto, or TON)',
        'Your Pro access is unlocked. Check your email for next steps.',
        500,
        'USD',
        false
    ),
    (
        'ton_pack',
        'TON Package',
        'Package priced in TON (amount_minor = nanoton)',
        'Your TON purchase is complete. Enjoy your package!',
        100000000,
        'TON',
        false
    )
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    delivery_content = EXCLUDED.delivery_content,
    amount_minor = EXCLUDED.amount_minor,
    currency = EXCLUDED.currency,
    is_digital = EXCLUDED.is_digital;

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
