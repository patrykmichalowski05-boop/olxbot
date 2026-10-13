BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    last_status TEXT NOT NULL
        CHECK(last_status IN (
            'ACTIVE',
            'REMOVED',
            'UNKNOWN'
        )),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(platform, external_id)
);

CREATE TABLE IF NOT EXISTS listing_observations (
    id TEXT PRIMARY KEY,
    listing_id TEXT NOT NULL REFERENCES listings(id),
    content_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(listing_id, content_hash)
);

CREATE TABLE IF NOT EXISTS valuation_runs (
    id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL
        REFERENCES listing_observations(id),
    engine_version TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    market_snapshot_id TEXT NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(
        observation_id,
        engine_version,
        policy_version,
        market_snapshot_id
    )
);

CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id),
    product_instance_id TEXT NOT NULL,
    purchase_minor BIGINT NOT NULL
        CHECK(purchase_minor > 0),
    sale_minor BIGINT
        CHECK(sale_minor > 0),
    currency CHAR(3) NOT NULL DEFAULT 'PLN',
    status TEXT NOT NULL
        CHECK(status IN ('BOUGHT', 'SOLD')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(owner_id, product_instance_id)
);

CREATE TABLE IF NOT EXISTS deal_costs (
    id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL REFERENCES deals(id),
    kind TEXT NOT NULL,
    amount_minor BIGINT NOT NULL
        CHECK(amount_minor >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'PLN',
    note TEXT NOT NULL DEFAULT '',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS deal_costs_deal_idx
ON deal_costs(deal_id);

CREATE TABLE IF NOT EXISTS idempotency_results (
    owner_id TEXT NOT NULL REFERENCES users(id),
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    response JSONB NOT NULL,
    PRIMARY KEY(owner_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS notification_outbox (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ
);

COMMIT;
